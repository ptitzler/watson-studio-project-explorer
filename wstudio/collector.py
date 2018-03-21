# -------------------------------------------------------------------------------
# Copyright IBM Corp. 2017
# 
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# -------------------------------------------------------------------------------

import json
import pandas as pd
import requests
import urllib


class Collector:
    def __init__(self, ibm_cloud_user_api_key=None, **kwargs):

        if ibm_cloud_user_api_key is None:
          raise Exception('You must specify an IBM Cloud user API key.')

        self.apikey =  ibm_cloud_user_api_key;
          
        self.verbose = True # TODO

        self.base_URL = 'https://api.dataplatform.ibm.com{}'
        self.UI_base_URL = 'https://dataplatform.ibm.com{}'
        self.token = self.getAccessToken()  # access token (including type, e.g. "Bearer 012345") or None


        self.data = {
            'projects' : [],
            'spaces': {},
            'services': {},         # used for name lookup only
            'service_plans': {},    # used for name lookup only
            'service_instances': []
        }

        # validate credentials
        #print(self.config)

    def getAccessToken(self):
        """
        Mint an access token using the provided id and password
        """
        headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded;charset=utf-8',
            'Authorization': 'Basic Yng6Yng='
        }

        response = requests.post('https://iam.ng.bluemix.net/identity/token',
                                 data='apikey={}&grant_type=urn%3Aibm%3Aparams%3Aoauth%3Agrant-type%3Aapikey'.format(self.apikey),
                                 headers=headers)

        if response.status_code == 200:
            return '{} {}'.format(response.json()['token_type'],response.json()['access_token'])
        else:
            raise Exception('Fatal error obtaining auth token. IBM Cloud returned {}.'.format(response))       

    def collect(self):
        """
        Collect information about Cloud Foundry service instances that the specified id has access to. Returns a Pandas DataFrame.
        """

        self.data['projects'] = []

        def fetch(url, limit = 100):
            http_headers = {
                'accept': 'application/json',
                'Authorization': self.token
            }

            response = requests.get(self.base_URL.format(url), headers=http_headers)
            if response.status_code == 200:
               response_json = response.json()
               for resource in response_json.get('resources', []):
                  self.data['projects'].append({'project_guid': resource['metadata']['guid'],
                                                'project_name': resource['entity']['name'],
                                                'project_storage_type': resource['entity'].get('storage', {}).get('type')
                                                })       
               return len(response_json.get('resources', [])) == limit
            else:
               raise Exception('Fatal error retrieving organization list: {}'.format(response))

        # https://apidocs.cloudfoundry.org/280/services/list_all_services.html
        url = '/v2/projects?skip={}&limit={}&include=everything'
        offset = 0
        limit = 10

        while fetch(url.format(offset, limit), limit):
            if self.verbose: 
              print('Searching for projects...')
            offset = offset + limit
        print('Found {} project(s).'.format(len(self.data['projects'])))    


        print('Data collection completed.')   

        # generate Pandas DataFrame and return it
        return pd.DataFrame(self.data['projects'])

        """
        load list of spaces that this id has access to
        """

        self.cfdata['spaces'] = {}

        def fetch(url):
            http_headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'authorization': self.token
            }
            response = requests.get(self.base_URL.format(url), headers=http_headers)
            if response.status_code == 200:
               for resource in response.json().get('resources', []):
                  self.cfdata['spaces'][resource['metadata']['guid']] = {
                    'space_name': resource['entity']['name'],
                    'org_guid': resource['entity']['organization_guid'],
                    'org_name': self.cfdata['organizations'][resource['entity']['organization_guid']]
                  }
               return response.json()['next_url']
            else:
             raise Exception('Fatal error retrieving space list (GET {}): {}'.format(url, response))

        # https://apidocs.cloudfoundry.org/280/organizations/list_all_spaces_for_the_organization.html
        for org_guid in self.cfdata['organizations'].keys(): 
            url = '/v2/organizations/{}/spaces?results-per-page=100'.format(org_guid)
            while url is not None:
               if self.verbose: 
                print(' Searching for spaces in organization {}...'.format(self.cfdata['organizations'][org_guid]))
               url = fetch(url)


        """
        load list of services (this is not user specific)

        """

        self.cfdata['services'] = {}

        def fetch(url):
            http_headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'authorization': self.token
            }
            response = requests.get(self.base_URL.format(url), headers=http_headers)
            if response.status_code == 200:
               for resource in response.json().get('resources', []):
                  self.cfdata['services'][resource['metadata']['guid']] = resource['entity']['label']          
               return response.json()['next_url']
            else:
               raise Exception('Fatal error retrieving service list (GET {}): {}'.format(url, response))

        # https://apidocs.cloudfoundry.org/280/services/list_all_services.html
        url = '/v2/services?results-per-page=100'

        while url is not None:
           url = fetch(url)


        """
        load list of service plans (this is not user specific)

        """

        self.cfdata['service_plans'] = {}

        def fetch(url):
            http_headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'authorization': self.token
            }
            response = requests.get(self.base_URL.format(url), headers=http_headers)
            if response.status_code == 200:
               for resource in response.json().get('resources', []):
                   self.cfdata['service_plans'][resource['metadata']['guid']] = resource['entity']['name']          
               return response.json()['next_url']                
            else:
               raise Exception('Fatal error retrieving service plan information (GET {}): {}'.format(url, response))

        # https://apidocs.cloudfoundry.org/280/service_plans/list_all_service_plans.html
        url = '/v2/service_plans?results-per-page=100'

        while url is not None:
            url = fetch(url)


        """
        load list of service instances that this id has access to

        """

        self.cfdata['service_instances'] = []

        def fetch(url):
            http_headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'authorization': self.token
            }
            response = requests.get(self.base_URL.format(url), headers=http_headers)
            if response.status_code == 200:     
                for resource in response.json().get('resources', []):
                   service = {'service_instance_name':resource['entity']['name'],
                              'service_instance_guid':resource['metadata']['guid'],
                              'service_guid':resource['entity']['service_guid'],
                              'created_at':resource['metadata']['created_at'],
                              'service_plan_guid': resource['entity'].get('service_plan_guid', None),
                              'space_guid': resource['entity'].get('space_guid', None)}
                
                   if self.cfdata['spaces'] is not None and self.cfdata['spaces'].get(service['space_guid'], None) is not None:
                       service['space_name'] = self.cfdata['spaces'][service['space_guid']]['space_name']
                       service['org_name'] = self.cfdata['spaces'][service['space_guid']]['org_name']
                       service['org_guid'] = self.cfdata['spaces'][service['space_guid']]['org_guid']
                        
                   if self.cfdata['services'] is not None and self.cfdata['services'].get(service['service_guid'], None) is not None:
                       service['service_name'] = self.cfdata['services'][service['service_guid']]
                   else:
                       service['service_name'] = None
                       print(' Warning. Found no service name for service "{}" guid "{}" in org "{}" space "{}"'.format(service['service_instance_name'],
                                                                                                                        service['service_guid'],
                                                                                                                        service['org_name'],
                                                                                                                        service['space_name']))                    
                    
                   if self.cfdata['service_plans'] is not None and self.cfdata['service_plans'].get(service['service_plan_guid'], None) is not None:
                        service['service_plan_name'] = self.cfdata['service_plans'][service['service_plan_guid']]
                   else:
                        service['service_plan_name'] = None
                        print(' Warning. Found no service plan name for service "{}" plan guid "{}" in org "{}" space "{}"'.format(service['service_instance_name'],
                                                                                                                                   service['service_plan_guid'],
                                                                                                                                   service['org_name'],
                                                                                                                                   service['space_name']))
                   self.cfdata['service_instances'].append(service)
                return response.json()['next_url']  
            else:
                raise Exception('Fatal error retrieving service instance information (GET {}): {}'.format(url, response))           

        # https://apidocs.cloudfoundry.org/280/service_instances/list_all_service_instances.html
        url = '/v2/service_instances?results-per-page=100'

        while url is not None:
           if self.verbose: 
              print('Searching for service instances...')
           url = fetch(url)

        print('Data collection completed.')   

        # generate Pandas DataFrame and return it
        return pd.DataFrame(self.cfdata['service_instances'])

