#Dividing GPS into regional matrices
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

lon_min = 120
lon_max = 0
lat_min = 120
lat_max = 0

for k in range(0,288):
    fileid=str(k)+'-'+str(k+1)+'.csv'
    filedate='xxxxx_Group/'
    dataf=pd.read_csv('data/'+filedate+fileid,header=0,index_col=0)
    print(dataf)

    lon_min0=dataf['2'].min()
    lon_max0=dataf['2'].max()
    lat_min0=dataf['1'].min()
    lat_max0=dataf['1'].max()
    if lon_min0 < lon_min:
        lon_min = lon_min0
    if lat_min0 < lat_min and lat_min0!=0:
        lat_min = lat_min0
    if lon_max0 > lon_max:
        lon_max = lon_max0
    if lat_max0 > lat_max:
        lat_max = lat_max0


    point_max=[xxx.179104,xx.768588] #Longitude and latitude in the upper right corner of the map
    point_min=[xxx.950863,xx.614556]  #Longitude and latitude in the bottom left corner of the map
    w=xx  #The width of the grid
    l=xx  #The height of the grid
    #Generate an empty array
    data = [[0]*w for i in range(l)]  #Column Rows

    m=(point_max[0]-point_min[0])/w
    n=(point_max[1]-point_min[1])/l
    if len(dataf)>0:
        for i in range(0,l):
            for j in range(0,w):
                dataf1 = dataf['0.1'][(dataf['2'] > point_min[0] + m * j) & (dataf['2'] < point_min[0] + m * (j + 1))
                                      & (dataf['1'] < point_max[1] - m * i) & (dataf['1'] > point_max[1] - m * (i+1))]
                data[i][j]=dataf1.count()
    else:
        data = [[0] * w for i in range(l)]
   
    dataf1=pd.DataFrame(data)






