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

from .collector import Collector
from .visualizer import Visualizer

class Browser:
    def __init__(self, ibm_cloud_user_api_key=None, **kwargs):
        """
        Gathers project information from IBM Watson Studio
        """

        # verify mandatory parameters
        if ibm_cloud_user_api_key is None:
          raise Exception('You must specify an IBM Cloud user API key.')

        # retrieve the required information from IBM Watson Studio
        self.service_instance_df = Collector(ibm_cloud_user_api_key = ibm_cloud_user_api_key).collect()

        # visualize the collected information
        # The following is a PixieApp, which expects invocation parameters to be passed to the run() method in a dictionary
        Visualizer().run({'data': self.service_instance_df,
                         'ibm_cloud_user_api_key': ibm_cloud_user_api_key})


    def getPandasDataFrame(self):
    	"""
    	Returns the gathers service instance information as a Pandas DataFrame
    	"""
    	return self.service_instance_df
