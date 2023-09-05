#To timestamp
import pandas as pd
import time, datetime

def datetotime(data1):
    # Convert to time array
    timeArray = time.strptime(data1, "%Y/%m/%d %H:%M:%S")
    # Convert to timestamp
    timeStamp = int(time.mktime(timeArray))
    return(timeStamp)

filepath='data/XXXXX.csv'
dataf=pd.read_csv(filepath,header=None,index_col=None)

dataf[4]=dataf[4].map(lambda x: datetotime(str(x)))

print(dataf[4])

dataf.to_csv('data/XXXXX_train_aftertime.csv')



