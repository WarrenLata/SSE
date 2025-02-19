#! /usr/bin/env python3
import argparse
import json
import logging
import logging.config
import os
import numpy as np
import sys
import time
from concurrent import futures
from datetime import datetime

# Add Generated folder to module path.
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PARENT_DIR, 'Generated'))

import ServerSideExtension_pb2 as SSE
import grpc
from SSEData_Test import FunctionType
from ScriptEval_Test import ScriptEval
import scipy.stats as stats
_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class ExtensionService(SSE.ConnectorServicer):
    """
    A simple SSE-plugin created based on the HelloWorld example.
    """

    def __init__(self, funcdef_file):
        """
        Class initializer.
        :param funcdef_file: a function definition JSON file
        """
        self._function_definitions = funcdef_file
        self.ScriptEval = ScriptEval()
        os.makedirs('logs', exist_ok=True)
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logger.config')
        logging.config.fileConfig(log_file)
        logging.info('Logging enabled')

    @property
    def function_definitions(self):
        """
        :return: json file with function definitions
        """
        return self._function_definitions

    @property
    def functions(self):
        """
        :return: Mapping of function id and implementation
        """
        return {
            0: '_hello_world',
            1: '_hello_world_aggr',
            2: '_cache',
            3: '_no_cache',
            4: '_my_test',
            5:'_my_corr'
        }

    @staticmethod
    def _get_function_id(context):
        """
        Retrieve function id from header.
        :param context: context
        :return: function id
        """
        metadata = dict(context.invocation_metadata())
        header = SSE.FunctionRequestHeader()
        header.ParseFromString(metadata['qlik-functionrequestheader-bin'])

        return header.functionId

    """
    Implementation of added functions.
    """

    @staticmethod
    def _hello_world(request, context):
        """
        Mirrors the input and sends back the same data.
        :param request: iterable sequence of bundled rows
        :return: the same iterable sequence as received
        """
        for request_rows in request:
            yield request_rows

    @staticmethod
    def _hello_world_aggr(request, context):
        """
        Aggregates the parameters to a single comma separated string.
        :param request: iterable sequence of bundled rows
        :return: string
        """
        params = []

        # Iterate over bundled rows
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]
                params.append(param)

        # Aggregate parameters to a single string
        result = ', '.join(params)

        # Create an iterable of dual with the result
        duals = iter([SSE.Dual(strData=result)])

        # Yield the row data as bundled rows
        yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])

    @staticmethod
    def _cache(request, context):
        """
        Cache enabled. Add the datetime stamp to the end of each string value.
        :param request: iterable sequence of bundled rows
        :param context: not used.
        :return: string
        """
        # Iterate over bundled rows
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]

                # Join with current timedate stamp
                result = param + ' ' + datetime.now().isoformat()
                # Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])

                # Yield the row data as bundled rows
                yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])

    @staticmethod
    def _no_cache(request, context):

        # Disable caching.
        md = (('qlik-cache', 'no-store'),)
        context.send_initial_metadata(md)

        # Iterate over bundled rows
        for request_rows in request:
            # Iterate over rows
            for row in request_rows.rows:
                # Retrieve string value of parameter and append to the params variable
                # Length of param is 1 since one column is received, the [0] collects the first value in the list
                param = [d.strData for d in row.duals][0]

                # Join with current timedate stamp
                result = param + ' ' + datetime.now().isoformat()
                # Create an iterable of dual with the result
                duals = iter([SSE.Dual(strData=result)])

                # Yield the row data as bundled rows
                yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])
    @staticmethod
    def _my_test(request, context):
        param_1 = []
        param_2 = []
        for request_row in request:
            for row in request_row.rows:
                x = [d.strData for d in row.duals][0]
                y = [d.strData for d in row.duals][1]
                if x and y:
                    param_1.append(x.replace(",", "."))
                    param_2.append(y.replace(",", "."))
        param_1 = list(map(float, param_1))
        param_2 = list(map(float, param_2))

        ## chek normality ###
        r, p = stats.shapiro(param_1)
        r1, p1 = stats.shapiro(param_2)

        if p<0.05 or p1<0.05:
            T, p_value = stats.mannwhitneyu(param_1, param_2)

        else:
            #### check variance   #########
            x = np.array(param_1)
            y = np.array(param_2)
            f = np.var(x, ddof=1) / np.var(y, ddof=1)  # calculate F test statistic
            dfn = x.size - 1  # define degrees of freedom numerator
            dfd = y.size - 1  # define degrees of freedom denominator
            p = 1 - stats.f.cdf(f, dfn, dfd)  # find p-value of F test statistic
            ### test ########
            T,p_value=stats.ttest_ind(param_1, param_2, equal_var=p<0.05)
        result = str(p_value)
        duals = iter([SSE.Dual(strData=result)])
        yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])

    @staticmethod
    def _my_corr(request, context):

        # compute corrélation between two field
        # return the p_value of the pearson correlation
        # as correlation already implemented
        x = []
        y = []
        for request_row in request:
            for row in request_row.rows:
                param_1 = [d.strData for d in row.duals][0]
                param_2 = [d.strData for d in row.duals][1]
                if param_1 and  param_2:
                    x.append(param_1.replace(",", "."))
                    y.append(param_2.replace(",", "."))

        x = list(map(float, x))
        y = list(map(float, y))
        result = str(stats.pearsonr(x, y)[1])

        duals = iter([SSE.Dual(strData=result)])

        yield SSE.BundledRows(rows=[SSE.Row(duals=duals)])

    @staticmethod
    def _Anova(self, request, context):
        # multi-test entre 3 variables ou plus
        # Non len(row.duals[0]) a le nombre de paramètre
        # working on it
        param1 = []
        param2 = []
        param3 = []

        for request_row in request:
            for row in request_row.rows:
                param = [d.strData for d in row.duals][0]
                param1.append(param)
                param = [d.strData for d in row.duals][1]
                param2.append(param)
                param = [d.strData for d in row.duals][2]
                param2.append(param)
        param1 = list(map(float, param1))
        param2 = list(map(float, param2))
        param3 = list(map(float, param3))

        return

    ############# RPC ########################################################################################################################

    """
    Implementation of rpc functions.
    """

    def GetCapabilities(self, request, context):
        """
        Get capabilities.
        :param request: the request, not used in this method.
        :param context: the context, not used in this method.
        :return: the capabilities.
        """
        logging.info('GetCapabilities')
        # Create an instance of the Capabilities grpc message
        # Enable(or disable) script evaluation
        # Set values for pluginIdentifier and pluginVersion
        capabilities = SSE.Capabilities(allowScript=True,
                                        pluginIdentifier='Test Stat - Qlik',
                                        pluginVersion='v1.0.0-beta1')

        # If user defined functions supported, add the definitions to the message
        with open(self.function_definitions) as json_file:
            # Iterate over each function definition and add data to the capabilities grpc message
            for definition in json.load(json_file)['Functions']:
                function = capabilities.functions.add()
                function.name = definition['Name']
                function.functionId = definition['Id']
                function.functionType = definition['Type']
                function.returnType = definition['ReturnType']

                # Retrieve name and type of each parameter
                for param_name, param_type in sorted(definition['Params'].items()):
                    function.params.add(name=param_name, dataType=param_type)

                logging.info('Adding to capabilities: {}({})'.format(function.name,
                                                                     [p.name for p in function.params]))

        return capabilities

    def ExecuteFunction(self, request_iterator, context):
        """
        Execute function call.
        :param request_iterator: an iterable sequence of Row.
        :param context: the context.
        :return: an iterable sequence of Row.
        """
        # Retrieve function id
        func_id = self._get_function_id(context)

        # Call corresponding function
        logging.info('ExecuteFunction (functionId: {})'.format(func_id))

        return getattr(self, self.functions[func_id])(request_iterator, context)

    def EvaluateScript(self, request, context):
        """
        This plugin provides functionality only for script calls with no parameters and tensor script calls.
        :param request:
        :param context:
        :return:
        """
        # Parse header for script request
        metadata = dict(context.invocation_metadata())
        header = SSE.ScriptRequestHeader()
        header.ParseFromString(metadata['qlik-scriptrequestheader-bin'])

        # Retrieve function type
        func_type = self.ScriptEval.get_func_type(header)

        # Verify function type
        if (func_type == FunctionType.Aggregation) or (func_type == FunctionType.Tensor):
            return self.ScriptEval.EvaluateScript(header, request, context, func_type)
        else:
            # This plugin does not support other function types than aggregation  and tensor.
            # Make sure the error handling, including logging, works as intended in the client
            msg = 'Function type {} is not supported in this plugin.'.format(func_type.name)
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details(msg)
            # Raise error on the plugin-side
            raise grpc.RpcError(grpc.StatusCode.UNIMPLEMENTED, msg)

    """
    Implementation of the Server connecting to gRPC.
    """
    # Set up grpc server 
    def Serve(self, port, pem_dir):
        """
        gRPC Server with insecure connection on port
        :param port: port to listen on.
        :param pem_dir: Directory including certificates
        :return: None
        """
        # Create gRPC server
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        SSE.add_ConnectorServicer_to_server(self, server)

        if pem_dir:
            # Secure connection if certififcate
            with open(os.path.join(pem_dir, 'sse_server_key.pem'), 'rb') as f:
                private_key = f.read()
            with open(os.path.join(pem_dir, 'sse_server_cert.pem'), 'rb') as f:
                cert_chain = f.read()
            with open(os.path.join(pem_dir, 'root_cert.pem'), 'rb') as f:
                root_cert = f.read()
            credentials = grpc.ssl_server_credentials([(private_key, cert_chain)], root_cert, True)
            server.add_secure_port('[::]:{}'.format(port), credentials)
            logging.info('*** Running server in secure mode on port: {} ***'.format(port))
        else:
            # Insecure connection
            server.add_insecure_port('[::]:{}'.format(port))
            logging.info('*** Running server in insecure mode on port: {} ***'.format(port))

        # Start gRPC server
        server.start()
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            server.stop(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', nargs='?', default='50052'
                        )
    parser.add_argument('--pem_dir', nargs='?')
    parser.add_argument('--definition_file', nargs='?', default='FuncDefs_helloworld.json')
    args = parser.parse_args()

    # need to locate the file when script is called from outside it's location dir.
    def_file = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), args.definition_file)

    calc = ExtensionService(def_file)
    calc.Serve(args.port, args.pem_dir)
