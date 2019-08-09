"""
Main Tuner Class which uses other abstractions.
Genereal usage is to find the optimal hyper-parameters of the classifier
"""

from mango.domain.domain_space import domain_space
from mango.optimizer.bayesian_learning import BayesianLearning

import numpy as np

##setting warnings to ignore for now
import warnings
warnings.filterwarnings('ignore')

class Tuner():
    def __init__(self, param_dict, objective, conf_dict=None):
        #stores the configuration used by the tuner
        self.conf_Dict = dict()

        #stores the results of using the tuner
        self.results = dict()


        #param_dict is a required parameter
        self.conf_Dict['param_dict'] = param_dict

        #Objective funtion is a required parameter
        self.conf_Dict['userObjective']=objective

        self.conf_Dict['domain_size'] = 5000
        self.conf_Dict['initial_random'] = 1
        self.conf_Dict['num_iteration'] = 20
        self.conf_Dict['objective'] = 'maximize'
        self.conf_Dict['batch_size'] = 1


        #in case the optional conf_dict is passed
        if conf_dict != None:
            if 'objective' in conf_dict:
                self.conf_Dict['objective']=conf_dict['objective']

            if 'num_iteration' in conf_dict:
                self.conf_Dict['num_iteration'] = conf_dict['num_iteration']

            if 'domain_size' in conf_dict:
                self.conf_Dict['domain_size'] = conf_dict['domain_size']

            if 'initial_random' in conf_dict:
                if conf_dict['initial_random']>0:
                    self.conf_Dict['initial_random'] = conf_dict['initial_random']

            if 'batch_size' in conf_dict:
                if conf_dict['batch_size']>0:
                    self.conf_Dict['batch_size'] = conf_dict['batch_size']



    def getConf(self):
        return self.conf_Dict

    """
    Main function used by tuner to run the classifier evaluation
    """
    def run(self):
        #running the optimizer
        self.results =  self.runBayesianOptimizer()
        return self.results


    """
    - Called by runLocal.
    - Used to locally evaluate the classifier
    - calls run_clf_local function which is available in scheduler.LocalTasks
    """
    def runBatchLocal(self, X_batch_list):
        results = []
        for hyper_par in X_batch_list:
            result = run_clf_local(self.conf_Dict['clf_name'], self.conf_Dict['dataset_name'], hyper_par)
            results.append(result)
        return np.array(results).reshape(len(results),1),results

    def runBayesianOptimizer(self):
        results = dict()
        #domain space abstraction
        ds = domain_space(self.conf_Dict['param_dict'],self.conf_Dict['domain_size'])


        #getting first few random values
        random_hyper_parameters = ds.get_random_sample(self.conf_Dict['initial_random'])
        X_init = ds.convert_GP_space(random_hyper_parameters)


        Y_init,Y_list = self.runUserObjective(random_hyper_parameters)

        #setting the initial random hyper parameters tried
        results['random_hyper_parameters'] = random_hyper_parameters
        results['random_hyper_parameters_objective']= Y_list


        Optimizer = BayesianLearning()
        Optimizer.domain_size = self.conf_Dict['domain_size']


        X_sample=X_init
        Y_sample=Y_init

        hyper_parameters_tried = random_hyper_parameters
        objective_function_values = Y_list

        #running the iterations
        for i in range(self.conf_Dict['num_iteration']):

            # Domain Space
            domain_list = ds.get_domain()
            X_domain_np = ds.convert_GP_space(domain_list)

            #Black-Box Optimizer
            X_next_batch = Optimizer.get_next_batch(X_sample,Y_sample,X_domain_np,batch_size=self.conf_Dict['batch_size'])


            #Scheduler
            X_next_PS = ds.convert_PS_space(X_next_batch)


            #Evaluate the Objective function
            Y_next_batch, Y_next_list = self.runUserObjective(X_next_PS)

            #update the bookeeping of values tried
            hyper_parameters_tried = hyper_parameters_tried + X_next_PS
            objective_function_values = objective_function_values + Y_next_list


            #Appending to the current samples
            X_sample = np.vstack((X_sample, X_next_batch))
            Y_sample = np.vstack((Y_sample, Y_next_batch))

        results['hyper_parameters_tried'] = hyper_parameters_tried
        results['objective_values'] = objective_function_values


        results['best_objective']=np.max(Y_sample)
        results['best_hyper_parameter'] = hyper_parameters_tried[np.argmax(Y_sample)]

        return results


    def runUserObjective(self,X_next_PS):
        results = self.conf_Dict['userObjective'](X_next_PS)
        return np.array(results).reshape(len(results),1),results