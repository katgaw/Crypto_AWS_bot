import pandas as pd
import numpy as np

def sortino_ratio(daily_returns):
    ''' Create a DataFrame that contains the Portfolio Daily Returns column 
    Args: daily_returns(dataframe): dataframe with daily returns
    '''

    sortino_ratio_df=pd.DataFrame()
    sortino_ratio_df['Portfolio Daily Returns']=daily_returns

    # Create a column to hold downside return values
    sortino_ratio_df['Downside Returns'] = 0

    # Find Portfolio Daily Returns values less than 0,
    # square those values, and add them to the Downside Returns column
    sortino_ratio_df.loc[sortino_ratio_df['Portfolio Daily Returns'] < 0,
                        'Downside Returns'] = sortino_ratio_df['Portfolio Daily Returns']**2

    # Calculate the Sortino ratio
    # Calculate the annualized return value
    annualized_return = (
        sortino_ratio_df['Portfolio Daily Returns'].mean() * 252
    )

    # Calculate the annualized downside standard deviation value
    downside_standard_deviation = (
        np.sqrt(sortino_ratio_df['Downside Returns'].mean()) * np.sqrt(252)
    )

    # The Sortino ratio is reached by dividing the annualized return value
    # by the downside standard deviation value
    sortino_ratio = annualized_return/downside_standard_deviation
    return sortino_ratio

def dataframe_for_forecasting(df):
    ''' Create dataframe with the target variable and its lagged values as features.

    Args: df(DataFrame): original dataframe with coin names, dates and prices.
    Returns: DataFrame with the target variable and its lagged values as features.

    '''
    df_past=pd.DataFrame() #declare an empty dataframe which will be populated with the lagged variables.
    df_all=pd.DataFrame() #declare an empty dataframe which will concat the variables across individual coins.
    for coin in df['coin'].unique():
        df_grouped=df.groupby('coin').get_group(coin)
        df_past['prices_t-1']=df_grouped['prices'].shift(1)
        df_past['prices_t-2']=df_grouped['prices'].shift(2)
        df_past['prices_t-3']=df_grouped['prices'].shift(3)
        df_coin=pd.concat([df_grouped,df_past],axis=1).dropna() #concat the dataframe with the target variable to the dataframe with features.
        df_coin=df_coin.drop(columns=['date','total_vol','market_caps']) #drop unnecessary columns.
        df_all=pd.concat([df_all,df_coin],axis=0) #concat the dataframe with features across individual currencies.
    return df_all

def create_id(df_all):
    ''' Create id column for each currency in the dataframe.
    Args: df_all(dataframe): dataframe with coin names, you want to populate with the coin id column.
    Returns: array with coin ids.
    '''
    grouped=df_all.groupby('coin')
    index=0
    coin_id=[]
    for coin in df_all['coin'].unique():
        index+=1
        coin_block=grouped.get_group(coin)
        coin_id=np.append(coin_id,np.repeat(index,len(coin_block)))
    return coin_id

def train_test_split(df_all):
    ''' Split dataframe into testing and training sets.

        Args: df_all(DataFrame): dataframe you want to split into testing and training sets.
        Returns: dataframes for each training and testing data.
    '''
    grouped=df_all.groupby('coin')
    train_all=pd.DataFrame()
    test_all=pd.DataFrame()
    for coin in df_all['coin'].unique():
        coin_block=grouped.get_group(coin)
        train=coin_block.iloc[0:181,:] #the training will be done on the first 181 days.
        test=coin_block.iloc[181:,:] #the testing will be done on the remaining days.
        train_all=pd.concat([train_all,train],axis=0) #concat the training sets across all currencies.
        test_all=pd.concat([test_all,test],axis=0)  #concat the testing sets across all currencies.
    return [train_all,test_all]

def portfolio_evaluation(df):
    ''' Function to create DataFrame combining risk as well as return indicators. 
    Args:
        df(DataFrame): DataFrame for calculating risk and return indicators.

    Returns:
        DataFrame with risk and return indicators calculated separately for each currency.
    '''
    # Create a list for the column name
    columns = df['coin'].unique()

    # Create a list holding the names of the new evaluation metrics
    metrics = [
        'Annualized Return',
        'Annual Volatility',
        'Sharpe Ratio',
        'Sortino Ratio',
        'Portfolio Cumulative Returns']

    # Initialize the DataFrame with index set to the evaluation metrics and the column
    portfolio_evaluation_df = pd.DataFrame(index=metrics, columns=columns)

    # Review the DataFrame
    for coin in df['coin'].unique():

        # get the block of the dataframe just for the specific coin
        signals_df = df.groupby('coin').get_group(coin)

        ####---------------------- RISK -----------------------------
        # Calculate annual returns
        daily_returns=signals_df['prices'].pct_change()
        portfolio_evaluation_df[coin].loc['Annualized Return'] = (
            daily_returns.mean() * 252
        )
        # Calculate annual volatility
        portfolio_evaluation_df[coin].loc['Annual Volatility'] = (
            daily_returns.std() * np.sqrt(252)
        )
        # Calculate Sharpe ratio
        portfolio_evaluation_df[coin].loc['Sharpe Ratio'] = (
        daily_returns.mean() * 252) / (
        daily_returns.std() * np.sqrt(252)
    )
        #Calculate Sortino ratio
        portfolio_evaluation_df[coin].loc['Sortino Ratio']=sortino_ratio(daily_returns)

        ####---------------------- ALGO-TRADING ----------------------
        # Set the short_window (50) and long window (100) variables
        short_window = 50
        long_window = 100

        # Generate the short and long moving averages (50 and 100 days, respectively)
        signals_df['SMA50'] = signals_df['prices'].rolling(window=short_window).mean()
        signals_df['SMA100'] = signals_df['prices'].rolling(window=long_window).mean()

        # Initialize the new Signal column to hold the trading signal
        signals_df['Signal'] = 0.0

        # Generate the trading signal 0 or 1,
        # where 1 is the short-window (SMA50) is less than the long-window (SMA100)
        signals_df["Signal"][short_window:] = np.where(
            signals_df["SMA50"][short_window:] < signals_df["SMA100"][short_window:], 1.0, 0.0
        )

        # Calculate the points in time at which a position should be taken, 1 or -1
        signals_df['Entry/Exit'] = signals_df['Signal'].diff()

        # Set the initial capital
        initial_capital = float(100000)

        # Set the share size
        share_size = -500

        # Take a 500 share position where the dual moving average crossover is 1 (SMA50 is greater than SMA100)
        signals_df["Position"] = share_size * signals_df["Signal"]

        # Find the points in time where a 500 share position is bought or sold
        signals_df["Entry/Exit Position"] = signals_df["Position"].diff()

        # Multiply share price by entry/exit positions and get the cumulatively sum
        signals_df["Portfolio Holdings"] = (
            signals_df["prices"] * signals_df["Entry/Exit Position"].cumsum()
        )

        # Subtract the initial capital by the portfolio holdings to get the amount of liquid cash in the portfolio
        signals_df["Portfolio Cash"] = (
            initial_capital - (signals_df["prices"] * signals_df["Entry/Exit Position"]).cumsum()
        )

        # Get the total portfolio value by adding the cash amount by the portfolio holdings (or investments)
        signals_df["Portfolio Total"] = (
            signals_df["Portfolio Cash"] + signals_df["Portfolio Holdings"]
        )

        # Calculate the portfolio daily returns
        signals_df["Portfolio Daily Returns"] = signals_df["Portfolio Total"].pct_change()

        # Calculate the cumulative returns
        signals_df["Portfolio Cumulative Returns"] = (
            1 + signals_df["Portfolio Daily Returns"]
        ).cumprod() - 1

        # Add the cumulative returns to the DataFrame
        portfolio_evaluation_df[coin].loc['Portfolio Cumulative Returns']=signals_df["Portfolio Cumulative Returns"].iloc[len(signals_df)-1]
    portfolio_evaluation_df=portfolio_evaluation_df.T.sort_values(by='Portfolio Cumulative Returns')
    return portfolio_evaluation_df