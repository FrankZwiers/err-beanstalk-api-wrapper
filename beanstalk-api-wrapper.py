#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from errbot import BotPlugin, botcmd

import sys, os

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import beanstalk_api
import logging

class beanstalk(BotPlugin):
	min_err_version = '1.6.0'

	def activate(self):
		super(beanstalk, self).activate()

		if not (set(("DOMAIN", "USERNAME", "PASSWORD", "EXCLUDE_USERS")) <= set(self.config)):
			logging.info("Not starting beanstalk, plugin not configured")

	def get_configuration_template(self):
		return {'DOMAIN': 'domain', 'USERNAME': 'username', 'PASSWORD': 'password', 'EXCLUDE_USERS': ['user1', 'user2']}

	def _connect_to_beanstalk(self):
		"""Connects to beanstalk via the api"""
		beanstalk_api.setup(self.config['DOMAIN'], self.config['USERNAME'], self.config['PASSWORD'])

	def _get_user_object_by_id(self, user_id):
		for user in self.users:
			if user['id'] == user_id:
				return user

	def _get_repository_object_by_id(self, repository_id):
		for repository in self.repositories:
			if repository['id'] == repository_id:
				return repository

	def _get_single_user_permissions(self, user_id):
		return  [beanstalk_api.api.permission.find(user_id)]

	def _get_all_permissions(self):
		return_data = []
		for user in self.users:
			return_data.append(self._get_single_user_permissions(user['id']))

		return return_data

	def _parse_permissions(self, raw_permissions):
		return_data = ''
		repository = None
		user = None

		for user_permissions in raw_permissions:
			for repository_permission in user_permissions[0]:
				if repository == None or repository['id'] != repository_permission['permission']['repository_id']:
					repository = self._get_repository_object_by_id(repository_permission['permission']['repository_id'])
				
				if user == None or user['id'] != repository_permission['permission']['user_id']:
					user = self._get_user_object_by_id(repository_permission['permission']['user_id'])
					user_full_name  = '{} {}'.format(user['first_name'], user['last_name'])
					return_data += '\nUser: {}\n'.format(user_full_name)
				return_data += 'Repository: {} | Permissions: Read {}, Write {}\n'.format(repository['name'], repository_permission['permission']['read'], repository_permission['permission']['write'])

		return return_data		

	def _get_all_users(self):
		"""Get all users from beanstalk and save them in self.users"""
		users = beanstalk_api.api.user.find()
		self.users = [user['user'] for user in users]

	def _get_all_repositories(self):
		"""Get all repositories from beanstalk and save them in self.repositories"""
                repositories = beanstalk_api.api.repository.find()
                self.repositories = [repository['repository'] for repository in repositories]
	
	def _prepare(self):
		"""This function connects to beanstalk and updates the users and repositories"""
		"""Should be called everytime err receives a beanstalk command"""
		self._connect_to_beanstalk()
                self._get_all_users()
		self._get_all_repositories()

	def _create_repository(self, name, title, vcs='git', label_color='label-white'):
		"""Perform create repository api call"""
		#beanstalk_api.api.repository.create(name, title, label_color, vcs)
		pass

	def _beanstalk_repository_set_permissions(self, repository_id, user_id):
		"""Perform create permissions api call"""
		#beanstalk_api.api.permission.create(user_id, repository, true, true, server_environment=None)
		pass

	def _get_user_id(self, login):
		"""Return the user id corresponding to the specified login name"""
		for user in self.users:
			if user['login'].strip() == login.strip():
				return user['id']

	def _get_repository_id(self, name):
		"""Return the repository id corresponding to the specified repository name"""
		for repository in self.repositories:
			if repository['name'].strip() == name.strip():
				return repository['id']	

	def _beanstalk_return_repositorydata(self, repository):
		"""Returns all data about the repository that was specified by the repository name"""
		repositorydata = ''
		for k,v in repository.iteritems():
			if k != 'title':
				repositorydata += "{0} : {1}\n".format(k, v)
		return repositorydata

	def _beanstalk_return_userdata(self, user):
		"""Returns all data about the user that was specified by the users login name"""
		userdata = ''
		for k,v in user.iteritems():
                	if k != 'first_name' and k != 'last_name':
                        	userdata += "{0} : {1}\n".format(k, v)
		return userdata

	def _is_valid_label_color(self, color):
		"""Check if the specified color is accepted by beanstalk"""
		valid_label_colors = ['white', 'red', 'orange', 'yellow', 'green', 'blue', 'pink', 'grey']
		if color in valid_label_colors:
			return True
		return False

	def _is_valid_vcs(self, vcs):
		"""Check if the specified version control system is accepted by beanstalk"""
		valid_vcs = ['svn', 'git', 'mercurial']
		if vcs in valid_vcs:
			return True
		return False

	def _parse_create_repository_arguments(self, args):
		"""Parse the arguments that should be specified when creating a repository"""
		args_len = len(args)

		# Check if the label color is valid
		if args_len > 2 and not self._is_valid_label_color(args[2]):
			return 2
		# Check if the specified vcs is valid
		if args_len > 3 and not self._is_valid_vcs(args[3]):
			return 3
		return True

	def _set_permissions_all_users(self, mess, args):
		"""Calls _set_permissions_single_user for every user in self.users"""
		repository_id = self._get_repository_id(args[0])

		if repository_id != None:
			return_data = "Setting permissions for repository: {}({})\n".format(args[0], repository_id)
			for user in self.users:
				args_single_user = [args[0], user['login']]
				return_data += self._set_permissions_single_user(mess, args_single_user)
			return return_data

	def _set_permissions_single_user(self, mess, args):
		"""Sets the permissions for a single user on a single repository"""
		repository_id = self._get_repository_id(args[0])
		user_id =  self._get_user_id(args[1])

		if repository_id != None and user_id != None and not (args[1] in self.config['EXCLUDE_USERS']):
			self._beanstalk_repository_set_permissions(repository_id, user_id)
			return "Set permissions for user: {0}({1})\n".format(args[1], user_id)
		else:
			if repository_id == None:
				return "Repository '{0}' not found\n".format(args[0])
			if user_id == None:
				return "User '{0}' not found\n".format(args[1])	

	@botcmd(split_args_with=' ')
 	def beanstalk_create_repository(self, mess, args):
		"""Err command that creates that calls the correct functions so the repository is created"""
		labels = ['Name', 'Title', 'Label-color', 'Vcs']
		args_len = len(args)
	
		if args_len < 2:
			args.append(args[0])
		if args_len < 3:
			args.append('white')
		if args_len < 4:
			args.append('git')
		
		parsed = self._parse_create_repository_arguments(args)

		if parsed == True:
			self._create_repository(args, args)
			return "Creating repository\n{}:{}\n{}:{}\n{}:{}\n{}:{}".format(labels[0], args[0], labels[1], args[1], labels[2], args[2], labels[3], args[3])
		else:
			return "'{}' is not a valid {}".format(args[parsed], labels[parsed])
	
	@botcmd
	def beanstalk_list_users(self, mess, args):
		"""Err command that outputs a list of users"""
		self._prepare()
		return_data = "\n"

		for user in self.users:
			userdata = self._beanstalk_return_userdata(user)
			return_data += "{0[first_name]} {0[last_name]}\n{1}\n".format(user, userdata)

		return return_data

        @botcmd
        def beanstalk_list_repositories(self, mess, args):
		"""Err command that outputs a list of repositories"""
                self._prepare()
		return_data = "\n"

                for repository in self.repositories:
			repositorydata = self._beanstalk_return_repositorydata(repository)
                        return_data += "{0[title]}\n{1}\n".format(repository, repositorydata)

		return return_data

	@botcmd
	def beanstalk_get_user_data(self, mess, args):
		"""Err command that outputs data about the specified user"""
		self._prepare()
		return_data = ''
		
		for user in self.users:
			if args == user['login']:
				return_data = self._beanstalk_return_userdata(user)

		if return_data != '':
			return "{}".format(return_data)
		else:
			return "The user '{}' does not exist".format(args)

	@botcmd
	def beanstalk_get_repository_data(self, mess, args):
		"""Err command that outputs data about the specified repository"""
		self._prepare()
		return_data = ''

		for repository in self.repositories:
			if args == repository['name']:
				return_data = self._beanstalk_return_repositorydata(repository)

		if return_data != '':
			return "{}".format(return_data)
		else:
			return "The repository '{}' does not exist".format(args)

	@botcmd(split_args_with=None)
	def beanstalk_set_permissions(self, mess, args):
		"""Err command that sets the standard permissions of a repository for all users or a single user"""
		self._prepare()
		num_args = len(args)

		# If the number of arguments equals 1 it should be a repository name
		if num_args == 1:
			return self._set_permissions_all_users(mess, args)
		# If the number of arguments equals 2 it should be a repository name and a user login
		elif num_args == 2:
			return self._set_permissions_single_user(mess, args)

	@botcmd(split_args_with=None)
	def beanstalk_get_permissions(self, mess, args):
		"""Err command that displays the permissions of all users or a single user"""
		self._prepare()
		num_args = len(args)
		
		# If the number of arguments equals 1 it should be a user login name
		if num_args == 1:
			user_id = self._get_user_id(args[0])
			if user_id != None:
				return self._parse_permissions([self._get_single_user_permissions(user_id)])
			else:
				return 'The user {} doesn\'t exist'.format(args[0])

		return self._parse_permissions(self._get_all_permissions())
