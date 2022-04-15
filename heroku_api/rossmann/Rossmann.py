import pickle
import inflection
import pandas as pd
import numpy as np
import math 
import datetime

class Rossmann( object ):
   def __init__(self):
      self.home_path = ''
      self.rs_competition_distance = pickle.load( open(  self.home_path + 'parameters/scaler_competition_distance.pkl', 'rb' ) )
      self.rs_competition_months =   pickle.load( open(  self.home_path + 'parameters/scaler_competition_time_months.pkl', 'rb' ) )
      self.mme_promo2_in_weeks =     pickle.load( open(  self.home_path + 'parameters/scaler_promo2_in_weeks.pkl', 'rb' ) )
      self.mme_year =                pickle.load( open(  self.home_path + 'parameters/scaler_year.pkl', 'rb' ) )
      self.encoder_store_type =      pickle.load( open(  self.home_path + 'parameters/encoder_store_type.pkl', 'rb' ) )
      self.df_mape = pd.read_pickle( 'parameters/df_mape.pkl' )


   def data_cleaning( self, df):

      cols_old = ['Store', 'DayOfWeek', 'Date', 'Open', 'Promo',
            'StateHoliday', 'SchoolHoliday', 'StoreType', 'Assortment',
            'CompetitionDistance', 'CompetitionOpenSinceMonth',
            'CompetitionOpenSinceYear', 'Promo2', 'Promo2SinceWeek',
            'Promo2SinceYear', 'PromoInterval']

      # Converting cols to snakecase
      snake_case = lambda x: inflection.underscore( x ) 
      cols_new = list( map( snake_case, cols_old) )

      # Renaming
      df.columns = cols_new

      # Data Types
      df['date'] = pd.to_datetime( df['date'] )

      #  NA Fillout
      df['competition_distance'].fillna(value = 200000.0, inplace = True)

      #competition_open_since_month
      df[ 'competition_open_since_month' ] = df.apply( lambda s: s['date'].month 
         if math.isnan( s['competition_open_since_month'] ) 
         else  s['competition_open_since_month'] , axis = 1)
      # replace NA with current date

      #competition_open_since_year
      df[ 'competition_open_since_year' ] = df.apply( lambda s: s['date'].year 
         if math.isnan( s['competition_open_since_year'] ) 
         else  s['competition_open_since_year'] , axis = 1)
      # replace NA with current date

      #promo2_since_week
      df[ 'promo2_since_week' ] = df.apply( lambda s: s['date'].week 
         if math.isnan( s['promo2_since_week'] ) 
         else  s['promo2_since_week'] , axis = 1)
      # replace NA with current date

      #promo2_since_year
      df[ 'promo2_since_year' ] = df.apply( lambda s: s['date'].year 
         if math.isnan( s['promo2_since_year'] ) 
         else  s['promo2_since_year'] , axis = 1)
      # replace NA with current date

      # promo_interval
      df['promo_interval'].fillna(0, inplace = True)

      df['month_map'] = df.apply( lambda s: s['date'].strftime('%b'), axis = 1 )

      # promo2 active?
      df['is_promo'] = df.apply( lambda s: 
         1 if (s['promo_interval'] !=0) and (s['month_map'] in s['promo_interval']) 
         else 0 , axis = 1)

      #Changing Data Types
      df['competition_open_since_month'] = df['competition_open_since_month'].astype(int)
      df['competition_open_since_year'] = df['competition_open_since_year'].astype(int)
      df['promo2_since_week'] = df['promo2_since_week'].astype(int)
      df['promo2_since_year'] = df['promo2_since_year'].astype(int)
      
      return df

   def feature_engineering(self, df2):
      # Extracting date time features for model usage
      # year 
      df2['year'] = df2['date'].dt.year

      # month
      df2['month'] = df2['date'].dt.month

      # day
      df2['day'] = df2['date'].dt.day

      # week of year
      df2['week'] = df2['date'].dt.isocalendar().week

      # year week
      df2['year_week'] = df2['date'].dt.strftime( '%Y-%W' )

      # competition since
      df2['competition_since'] = df2.apply(lambda x: datetime.datetime(
               year = x['competition_open_since_year'], 
               month = x['competition_open_since_month'],
               day = 1), axis = 1 )

      # competition Time in months
      df2['competition_time_months'] = ( ( df2.date - df2['competition_since'] )/30 ).apply( lambda x: x.days ).astype(int)

      # time since promo2 started in weeks
      df2['promo2_in_weeks'] = df2['promo2_since_year'].astype(str) + '-' + df2['promo2_since_week'].astype(str) + '-1'
      df2['promo2_in_weeks'] = df2['promo2_in_weeks'].apply( lambda x: datetime.datetime.strptime(x, "%Y-%W-%w") ) - datetime.timedelta( days=7 )
      df2['promo2_in_weeks'] = ( ( df2['date'] - df2['promo2_in_weeks'] )/7 ).apply( lambda x: x.days).astype(int)

      # assortment mapping
      df2['assortment'] = df2['assortment'].apply( lambda x: 'basic' if x == 'a' else 'extra' if x == 'b' else 'extended' )

      # holiday mapping
      df2['state_holiday'] = df2['state_holiday'].apply(lambda x: 'regular_day' if x== '0'
         else 'public_holiday' if x == 'a'
         else 'easter_holiday' if x == 'b'
         else 'christmas' )

   # Removing observations where store is closed and/or sales == 0
      df2 = df2.loc[ (df2['open']!= 0) ].copy()

      # Removing customers (won't have that for prediction since it's a future information) and other variables that won't be used
      cols_drop = [ 'open', 'promo_interval', 'month_map']
      df2.drop( cols_drop, axis = 1, inplace = True)

      return df2

   def data_preparation( self, df5):
      ## 5.1 Numerical Variables Preparation

      #competition_distance
      df5['competition_distance'] = self.rs_competition_distance.transform(df5[['competition_distance']].values)

      #competition_time_months
      df5['competition_time_months'] = self.rs_competition_months.transform(df5[['competition_time_months']].values )

      #promo2_in_weeks
      df5['promo2_in_weeks'] = self.mme_promo2_in_weeks.transform(df5[['promo2_in_weeks']].values )

      #year
      df5['year'] = self.mme_year.transform(df5[['year']].values )

      ## 5.2.0 Categorical Data Encoding
      # store_type
      df5['store_type'] = self.encoder_store_type.transform(df5[['store_type']].values )

      # assortment
      assortment_dict = { 'basic':1, 'extra':2, 'extended':3 }
      df5['assortment'] = df5['assortment'].map( assortment_dict )

      ## 5.3 Cyclical Transformation
      # month
      df5['month_sin'] = df5['month'].apply( lambda x: np.sin( (2.0*np.pi*x)/12.0 ) )
      df5['month_cos'] = df5['month'].apply( lambda x: np.cos( (2.0*np.pi*x)/12.0 ) )

      # week
      df5['week_sin'] = df5['week'].apply( lambda x: np.sin( (2.0*np.pi*x)/52 ) )
      df5['week_cos'] = df5['week'].apply( lambda x: np.cos( (2.0*np.pi*x)/52 ) )

      # day
      df5['day_sin'] = df5['day'].apply( lambda x: np.sin( (2.0*np.pi*x)/31 ) )
      df5['day_cos'] = df5['day'].apply( lambda x: np.cos( (2.0*np.pi*x)/31 ) )

      # day of week sin
      df5['day_of_week_sin'] = df5['day_of_week'].apply( lambda x: np.sin( (2.0*np.pi*x)/7.0 ) )
      df5['day_of_week_cos'] = df5['day_of_week'].apply( lambda x: np.cos( (2.0*np.pi*x)/7.0 ) )

      #df5.fillna(0, inplace = True) # df5 has no holiday and therefore came with NA

      ## 6.1 Spliting Dataframe into Train Test 
      cols_selected = ['store', 'promo', 'store_type', 'assortment', 'competition_distance', 'competition_open_since_month',
      'competition_open_since_year', 'promo2', 'promo2_since_week', 'promo2_since_year', 'competition_time_months', 
      'promo2_in_weeks', 'month_sin', 'month_cos', 'week_sin', 'week_cos', 'day_sin', 'day_cos', 'day_of_week_sin', 'day_of_week_cos']
      
      return df5[ cols_selected ]

   def predict( self, model, original_data, test_data ):
      pred = model.predict( test_data )      
      
      # joining pred with original data
      original_data['sales_prediction'] = np.expm1( pred )
      
      # joining MAPE for each store with returned dataframe
      original_data = original_data.merge( self.df_mape, how = 'inner', on = 'store' )

      return original_data.to_json( orient = 'records', date_format = 'iso')
