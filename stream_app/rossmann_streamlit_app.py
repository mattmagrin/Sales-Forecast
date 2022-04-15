import pandas as pd
import requests
import json
from PIL import Image
import streamlit as st

# Recieves dataframe,requests prediction to API and returns predictions as dataframe
@st.cache(allow_output_mutation=True)
def call_api( data ):
    # Transform data to json format
    data = json.dumps( data.to_dict('records') )

    #Call api
    url = 'https://rossmann-xgb-api.herokuapp.com/rossmann/predict'
    header = {'Content-type' : 'application/json'}
    data = data
    r = requests.post( url, data = data, headers = header )

    # Return status and data
    print( 'Status Code {}'.format( r.status_code ) )
    json_data = r.json()
    df = pd.DataFrame.from_dict( json_data )
    return df

# Receives selected period and returns train dataset (with sales and customers columns)
@st.cache(allow_output_mutation=True)
def select_train_df(period):
    global train
    train_df = train.loc[ train['Open'] != 0 ]

    train_dates = train_df['Date'].unique().tolist()
    train_dates.reverse()
    if period == '2014':
        min_date = test_dates[0].replace('2015', '2014')
        max_date = test_dates[-1].replace('2015', '2014')
    elif period == '2013':
        min_date = test_dates[0].replace('2015', '2014')
        max_date = test_dates[-1].replace('2015', '2014')
    else:
        min_date = train_dates[0]
        max_date = train_dates[-1]
    train_df = train_df.loc[ (train_df['Date'] >= min_date) & 
                             (train_df['Date'] < max_date) & 
                             (train_df['Store'].isin(stores_multiselect) ) ]

    train_df = pd.merge( train_df, df_store_raw, how = 'left', on = 'Store' )
    return train_df

# Calculates sales prediction expected error / uncertainty from predictions dataset
@st.cache(allow_output_mutation=True)
def result_calculation(predictions_dataset):
    res = predictions_dataset[[ 'store', 'sales_prediction', 'MAPE']].copy()
    res['best_scenario'] = res['sales_prediction']  + res['sales_prediction']*res['MAPE']
    res['worst_scenario'] = res['sales_prediction'] - res['sales_prediction']*res['MAPE']
    res['uncertainty'] = res['sales_prediction']*res['MAPE']
    res = res.groupby('store').sum().reset_index()
    res.drop('MAPE', axis =1, inplace = True)
    res = res.rename( columns = {'store': 'Store',	'sales_prediction': 'Sales Prediction',	'best_scenario': 'Best Scenario', 'worst_scenario': 'Worst Scenario', 'uncertainty': 'Uncertainty'} )
    return res

# ---------------------------------- #
# Loading objects

# Loading train datasets
train = pd.read_csv('train.csv', low_memory = False)

# Loading dataset to predict salesSS
df_store_raw = pd.read_csv('store.csv', low_memory = False)
df_test_raw =  pd.read_csv('test.csv',  low_memory = False)

# Merging test dataset with store dataset
df_test = pd.merge( df_test_raw, df_store_raw, how = 'left', on = 'Store' )

stores = df_test['Store'].unique();
test_dates = df_test['Date'].unique().tolist()
test_dates.reverse()

image = Image.open('Rossmann_logo.jpg')

# ---------------------------------- #
# Defining sidebar widgets
st.sidebar.write('#### Select a store:')
stores_multiselect = st.sidebar.multiselect('', stores)
st.sidebar.write('#### Select a period to compare predictions:')
period = st.sidebar.selectbox('',
        ['2014', '2013', 'Entire dataset'] )

toogle_all = st.sidebar.checkbox('Show all stores predictions dataset', value = False)

# ---------------------------------- #
# Ploting predictions for a store

"""
# Rossmann Stores Sales Predictions 
"""

if stores_multiselect != []:
    # Selecting desired store
    df_test = df_test.loc[ df_test['Store'].isin( stores_multiselect ) ]

    # Droping closed days and Id column
    df_test = df_test.loc[ df_test['Open'] != 0 ] 
    df_test.drop( 'Id', axis = 1, inplace = True)

    # Caling API
    ds_pred = call_api( df_test )

    # Calculating Results
    result = result_calculation(ds_pred)

    # Ploting result table
    st.write('## Sales Prediction for store: {} in next 6 weeks'.format(stores_multiselect[0]) )
    st.table(result.style.format( {'Sales Prediction' : '{:,.2f}',
                                            "Best Scenario" : "{:,.2f}",
                                            "Worst Scenario" : "{:,.2f}",
                                            "Uncertainty" : "{:,.2f}"} ))

    #creating dataset to plot

    """
    ## Sales Prediction Chart
    """

    pred_plot = ds_pred[['date', 'sales_prediction']].copy()
    pred_plot['date'] = pd.to_datetime( pred_plot['date'] )
    pred_plot = pred_plot.rename( columns= {'date': 'index'}).set_index('index')
    st.line_chart( pred_plot )

    # ---------------------------------- #
    # Plot predictions for a period in past
    
    if period in ['2014', '2013']:
        st.write('## Actual Sales X Prediction Chart for the same period in {}'.format(period) )
    else:
        st.write('## Actual Sales X Prediction Chart for the {}'.format(period))

    # Selecting period
    train_df = select_train_df(period)
    train_drop = train_df.drop(['Sales', 'Customers'], axis = 1).copy()
    # Caling API
    train_pred = call_api( train_drop )

    # Creating dataset to plot
    train_plot = train_df[['Date', 'Sales']]
    train_plot['Sales Prediction'] = train_pred['sales_prediction']
    train_plot['Date'] = pd.to_datetime( train_plot['Date'])
    train_plot = train_plot.rename( columns = {'Date' : 'index', 'Sales' : 'Actual Sales'} ).set_index('index')

    st.line_chart(train_plot)

    # ---------------------------------- #
    # Ploting prediction results for all stores in test dataset

    """
    ## Expected Total Revenue: 
    """


    # Selecting all  stores
    df_test_all_stores = pd.merge( df_test_raw, df_store_raw, how = 'left', on = 'Store' )

    # Droping closed days and Id column
    df_test_all_stores = df_test_all_stores.loc[ df_test_all_stores['Open'] != 0 ] 
    df_test_all_stores.drop( 'Id', axis = 1, inplace = True)

    # Caling API
    ds_pred_all_stores = call_api( df_test_all_stores )

    all_stores = result_calculation( ds_pred_all_stores )
    #all_stores.drop('Store', axis = 1, inplace = True)
    all_stores = all_stores.sum().reset_index().T
    all_res = all_stores.iloc[1:2, 1:5]
    all_res.columns = all_stores.iloc[0,1:5]
    all_res = all_res.astype('float64')
    st.table(all_res.style.format("{:,.2f}") )

    # Plot Expected Revenue Revenue 
    """
    ### Expected Revenue Chart: 
    """

    all_plot = ds_pred_all_stores[['date','sales_prediction']].groupby('date').sum().reset_index()
    all_plot['date'] = pd.to_datetime(all_plot['date'])
    all_plot = all_plot.rename(columns={ 'date' : 'index', 'sales_prediction' : 'Sales Prediction' } ).set_index('index')
    st.line_chart( all_plot )

    if toogle_all :
        st.write( '### All Stores Sales Predictions' )
        st.write( "##### Explore dataset by clicking on the columns' names" )
        explore = ds_pred_all_stores[['store', 'sales_prediction']].groupby('store').sum().reset_index()
        aux = ds_pred_all_stores[['store_type', 'assortment', 'store', 'competition_distance']].groupby('store').last().reset_index()
        final = explore.merge( aux, how = 'inner', on = 'store' )
        final = final.rename(columns = { 'store': 'Store', 'sales_prediction': 'Sales Prediction', 'store_type' : 'Store Type', 'assortment' : 'Assortment', 'competition_distance' : 'Competition Distance' })
        st.dataframe( final.style.format( {"Sales Prediction" : "{:,.2f}", "Competition Distance" : "{}" } ) ) #precision = 2

else:
    st.write('')
    st.write('### Select a store on the options box to the left and start exploring')
    st.write('')
    st.write('')
    st.image( image )

st.write( '###### App designed by: Matheus de Oliveira Magrin' )
st.write( '###### Find me through [LinkedIn](https://www.linkedin.com/in/matheusmagrin/)')