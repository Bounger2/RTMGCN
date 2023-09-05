#Coordinate points with the same cluster ID
import pandas as pd

for i in range(0,288):
    fileid=str(i)+'-'+str(i+1)+'.csv'
    filedate='xxxxx/'
    dataf=pd.read_csv('data/'+filedate+fileid,header=0,index_col=0)
    if len(dataf)>0:
        dataf1=dataf[['0','1','2']].groupby(dataf['0']).mean()
    else:
        dataf1=dataf
    dataf1.to_csv('data/xxxxx_Group/'+fileid)
    print('down', str(i))