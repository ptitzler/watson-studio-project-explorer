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
from pixiedust.display.app import *
import json
import requests

@PixieApp
@Logger()
class Visualizer():
    
    def setup(self):
        '''
        Initialize the app
        '''

        self.debug("Entering method setup")
        
        self.projects_df = self.pixieapp_entity.get('data', None)
        if self.projects_df is None:
            raise Exception("You must specify a Pandas DataFrame: {'data': <populated DataFrame>}")


        self.api_key = self.pixieapp_entity.get('ibm_cloud_user_api_key', None)
        if self.api_key is None:
          raise Exception('You must specify an IBM Cloud user API key.')  

        # in case any service name lookups or service plan name lookups failed, replace None with a descriptive meta string 
        # self.projects_df = self.projects_df.fillna(value={'service_plan_name':'[UNKNOWN/DISCONTINUED]', 'service_name':'[UNKNOWN/DISCONTINUED]'})
        
        # pre-compute service type list
        # self.service_types_df = self.projects_df[['project_guid', 'service_name']].drop_duplicates().sort_values(by=['service_name'])
        
        self.api_base_URL = 'https://api.dataplatform.ibm.com{}'

        # Mint an access token using the api key
        headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded;charset=utf-8',
            'Authorization': 'Basic Yng6Yng='
        }

        response = requests.post('https://iam.ng.bluemix.net/identity/token',
                                 data='apikey={}&grant_type=urn%3Aibm%3Aparams%3Aoauth%3Agrant-type%3Aapikey'.format(self.api_key),
                                 headers=headers)

        if response.status_code == 200:
            self.token = '{} {}'.format(response.json()['token_type'],response.json()['access_token'])
        else:
            raise Exception('Fatal error obtaining auth token. IBM Cloud returned {}.'.format(response))   

        # holds current filter selections
        self.state = {
            'filter': {
                'project_storage_type': None
            }
        }

    
    @route()
    @templateArgs 
    def main_screen(self):
        '''
        Define the UI layout: filters, project list and ...
        '''
        
        self.debug("Entering method main screen")
        
        # mark all projects visible by default. filters will override this setting
        self.projects_df['hide'] = False
        
        return """
            <!-- custom styling -->
            <style>
                div.outer-wrapper {
                    display: table;width:100%;height:100px;
                }
                div.inner-wrapper {
                    display: table-cell;vertical-align: middle;height: 100%;width: 100%;
                }
                th { text-align:center; }
                td { text-align: left; }
            </style>

            <!-- filters -->
            <div class="outer-wrapper" 
                 id="filters{{prefix}}"
                 pd_target="filters{{prefix}}"
                 pd_options="op=display_filters"
                 pd_render_onload
                 class="no_loading_msg">
            </div> 
        
            <!-- project list --> 
            <div class="outer-wrapper" 
                 id="matching_project_list{{prefix}}"
                 pd_target="matching_project_list{{prefix}}"
                 pd_options="op=display_project_list"
                 pd_render_onload>
            </div>
        
            <!-- service instance credentials --> 
            <div class="outer-wrapper" 
                 id="credentials_list{{prefix}}"
                 pd_target="credentials_list{{prefix}}"
                 pd_options="op=clear_credentials">

            </div>     
        """

       
    @route(op="display_filters")
    @templateArgs
    def display_filters(self):
        '''
        This PixieApp route refreshes the service, service plan, organization and space filters based on the current state
        '''

        self.info("Entering method display_filters: {}".format(self.state['filter']['project_storage_type']))

        # helpers: temporarily store filter options 
        project_storage_type_filter_options = {}

    
        for index, row in self.projects_df.iterrows():             
          project_storage_type_filter_options[row['project_storage_type']] = row['project_storage_type'] 
             

        # sort filter options using the display name (case-insentitive)
        sorted_project_storage_type_filter_options_keys = sorted(project_storage_type_filter_options, key=lambda k: project_storage_type_filter_options.get(k,'').lower())

        
        # debug
        self.info('sorted_project_storage_type_filter_options_keys: {}'.format(sorted_project_storage_type_filter_options_keys))
        
        # render context-sensitive filters
        return  """
            <select id="storage_type_filter{{prefix}}" 
                    pd_script="self.reset_selected_storage_type_filter('$val(storage_type_filter{{prefix}})')"
                    pd_refresh="filters{{prefix}},matching_project_list{{prefix}},credentials_list{{prefix}}"
                    class="no_loading_msg">
                <option value="---ALL---">--- All storage types ---</option>
            {% for storage_type_name in sorted_project_storage_type_filter_options_keys %}
              {% if this['state']['filter']['project_storage_type'] == storage_type_name %}
                <option value="{{storage_type_name}}" selected>{{storage_type_name}}</option>
              {% else %}
              <option value="{{storage_type_name}}">{{storage_type_name}}</option>
              {%endif %}  
            {% endfor %}                             
            </select>     
        """
   
    @route(op="display_project_list")
    @templateArgs
    def display_project_list(self):
        """
        This PixieApp route refreshes the list of service instances that meet the current filter condition
        """
        
        self.info("Entering method display_project_list: {}".format(self.state['filter']['project_storage_type']))
            
        # define filter function
        def filter_df(r, project_storage_type = None):
            """ Return True if this row should be hidden
            """
            if project_storage_type is not None and project_storage_type != r['project_storage_type']:
                return True
            return False
        
        # apply filter function on DataFrame, setting field hide_service_instance to True or False for each row, as appropriate
        self.projects_df['hide'] = self.projects_df.apply(filter_df, 
                                                          axis = 1, 
                                                          project_storage_type = self.state['filter']['project_storage_type'])

        # compose list summary message: "Showing X of Y service instances"
        stats = self.projects_df.groupby(by='hide').size().values
        if len(stats) == 1:
            count_msg = 'Showing {} of {} projects'.format(stats[0], stats[0])
        else:
            count_msg = 'Showing {} of {} projects'.format(stats[0], stats[0] + stats[1])
        
        # render list of projects that are not marked as hidden
        return  """
         <div>
         {{count_msg}}
         </div>
         <table class="table">
           <thead>
             <tr>
                <th>Project Name</th>
                <th>Storage Type</th>
                <th>Actions</th>
             </tr>
          </thead>
          <tbody>
          {% for row in this.projects_df.sort_values(by=['project_name']).itertuples()%}
           {% if row['hide'] == False %}
            <tr>
                <td>{{row['project_name']}}</td>
                <td>{{row['project_storage_type']}}</td>
                <td><button class="btn btn-default" type="button" pd_options="project_guid={{row['project_guid']}}" pd_target="credentials_list{{prefix}}">View details</button></td>
            </tr>
           {% endif %}
          {% endfor %}
          </tbody>
         </table>
        """
    
        @route(op="clear_credentials")
        def clear_credentials(self):
            return """
            """
    
    
    @route(project_guid="*")
    @templateArgs
    def list_credentials(self, project_guid):
        """
        This PixieApp route retrieves and displays the service credentials for the selected service instance
        """
        
        self.debug("Entering method list_credentials: {}".format(project_guid))
               
        # result data structure
        service_instance_credentials = []
        
    
        return """
            <h3>NOT IMPLEMENTED</h3>
            """
    
    def reset_selected_storage_type_filter(self, storage_type=None):
        """
        Helper: set service filter to the specified guid and reset all dependent filters
        """
        self.info("Resetting storage type filter to {}".format(storage_type))
        
        if storage_type == '---ALL---':
            # no specific type was selected
            storage_type = None
            
        self.state['filter'] = {
            'project_storage_type': storage_type
        }
        return
    
    
    