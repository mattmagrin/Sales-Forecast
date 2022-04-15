import pandas as pd
import requests
import json
import os
from flask import Flask, request, Response

token_json = open('token.json')
token = json.load(token_json)
token = token['token']

# send message to user
def send_message( chat_id, message ):
    # defining url to send message through requests
    url = 'https://api.telegram.org/bot{}/'.format( token ) 
    url = url + 'sendMessage?chat_id={}'.format( chat_id ) 
    
    r = requests.post( url, json = {'text' : message} )
    print( 'Status code {}'.format( r.status_code ) )
    
    return None

# Loading new unused data for testing
def data_preprocessing( store_id ):
    # read raw dataset
    store_id = int(store_id)
    df_store_raw = pd.read_csv('store.csv', low_memory = False)
    df_test_raw =  pd.read_csv('test.csv', low_memory = False)

    # Merging test dataset with store dataset
    df_test = pd.merge( df_test_raw, df_store_raw, how = 'left', on = 'Store' )
           
    # Selecting a store
    df_test = df_test[ df_test['Store'] == store_id  ].copy() #, 500, 1000

    # Check if store_id is valid
    if not df_test.empty:
        
        # Droping closed days and Id column
        df_test = df_test.loc[ df_test['Open'] != 0 ].copy()
        df_test.drop( 'Id', axis = 1, inplace = True)
        # Converting data to json
        json_data  = json.dumps( df_test.to_dict('records') )
    else:
        json_data = 'store_doesnt_exist'

    return json_data

def call_api( json_data ):
    # Calling API on Heroku
    url = 'https://rossmann-xgb-api.herokuapp.com/rossmann/predict'
    header = {'Content-type' : 'application/json'}

    response = requests.post( url, data = json_data, headers = header )

    print( 'Status Code {}'.format( response.status_code ) )
    api_response = response.json()
    return api_response

def eval_result( api_response ):
    df_mape = pd.read_pickle( open('df_mape.pkl', 'rb' ) )

    # creating results df
    res = pd.DataFrame.from_dict( api_response )

    res = res[['store', 'sales_prediction']].groupby('store').sum().reset_index()
    res = res.merge( df_mape, how = 'inner', on = 'store' )
    res['best_scenario'] = res['sales_prediction'] + res['sales_prediction']*res['MAPE'] 
    res['worst_scenario'] = res['sales_prediction'] - res['sales_prediction']*res['MAPE'] 
    res['uncertainty'] = res['sales_prediction']*res['MAPE'] 

    return res

def parse_message( message_received ):
    chat_id = message_received['message']['from']['id']
    store_id = message_received['message']['text']

    #store_id = store_id.replace('/', '')
    try:
        store_id = int( store_id )
    except ValueError:
        store_id = 'error'
    return chat_id, store_id

# API
app = Flask(__name__)

@app.route( '/', methods = ['GET', 'POST'] )
def index():
    
    # if a message is received
    if request.method == 'POST':
        message_received = request.get_json()
        
        chat_id, store_id = parse_message( message_received )

        # check if store_id is a number 
        if store_id != 'error':
            json_data = data_preprocessing( store_id )
            
            #check if store_id in dataframe and return prediction
            if json_data != 'store_doesnt_exist':
                
                # call xgb model API 
                api_response = call_api( json_data )
                
                # evaluate result and uncertainty 
                res = eval_result( api_response )
                
                # define all result variables that will be displayed to user
                pred = res['sales_prediction'][0]
                high_range = res['best_scenario'][0]
                low_range = res['worst_scenario'][0]

                # sends result as message to user
                send_message( chat_id, 'Store {} sales for next 6 weeks estimated at: $ {:,.2f}'.format(store_id, pred) )
                send_message( chat_id, 'Prediction might vary from $ {:,.2f} to $ {:,.2f}'.format(low_range, high_range) )
                return Response( 'Ok', status = 200 )
            
            else: #store_id not found in DF
                send_message( chat_id, "Store {} doesn't exist".format(store_id) )
                return Response( 'Ok', status = 200)
            
        # if store_id not valid, return status = 200 to exit  API loop  
        else:
            send_message( chat_id, 'Store ID not understood' )
            return Response( 'Ok', status = 200)
    
    # bot html welcome
    else:
        return '<h1> Rossman Stores Telegram BOT </h1>'

if __name__ == '__main__':
    # app.run( host='0.0.0.0', port=5000 )
    
    port = os.environ.get( 'PORT', 5000 )
    app.run( host = '0.0.0.0', port = port )
    