import os
import pandas as pd
import pickle
from flask import Flask, request, Response
from rossmann.Rossmann import Rossmann

# loading model
model = pickle.load( open('model/xgb_tuned_model.pkl', 'rb') )

# loading past MAPE for each store
#df_mape = pd.read_pickle( '~/DS/Rosmmann/parameters/df_mape.pkl' )

# initializing API
app = Flask( __name__ )

@app.route( '/rossmann/predict', methods = ['POST'] )
def rossmann_predict():
    test_json = request.get_json()

    if test_json: # data recieved
        if isinstance( test_json, dict ): # single observation
            test_raw = pd.DataFrame( test_json, index = [0] )
        
        else: # multiple observations
            test_raw = pd.DataFrame( test_json, columns = test_json[0].keys() )
            
        # Instantiating Rossmann class
        pipeline = Rossmann()
    
        # Data Cleaning
        df1 = pipeline.data_cleaning( test_raw )
        
        # Feature Engineering
        df2 = pipeline.feature_engineering( df1 )
        
        # Data Preparation
        df3 = pipeline.data_preparation ( df2 )
        
        # Prediction
        df_result = pipeline.predict( model, test_raw, df3 )

        return df_result

    else:
        return Response( '{}', status = 200, mimetype = 'application/json' )

if __name__ == '__main__':
    port = os.environ.get( 'PORT', 5000 )
    app.run( host='0.0.0.0', port = port )