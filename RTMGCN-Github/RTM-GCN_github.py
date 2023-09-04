#RTM-GCN (Simplified version of raster features)
import torch
import shutil
import torch.nn as nn
import torch.nn.functional as F
import pandas as pd
import numpy as np
import networkx as nx
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torch.autograd import Variable
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['backend'] = 'SVG'
import time
import os


# Standardization of adjacency matrix
def normalize(A, symmetric=True):
    d = A.sum(1)
    if symmetric:
        # D = D^-1/2
        D = torch.diag(torch.pow(d, -0.5).to(device))  # Transforming into a degree matrix
        return D.mm(A).mm(D)
    else:
        # D=D^-1
        D = torch.diag(torch.pow(d, -1).to(device))
        return D.mm(A)

# Self attention mechanism
class selfattention(nn.Module):
    def __init__(self, in_channels):
        super().__init__()
        self.in_channels = in_channels
        self.query = nn.Conv2d(in_channels, in_channels // 8, kernel_size=1, stride=1)
        self.key = nn.Conv2d(in_channels, in_channels // 8, kernel_size=1, stride=1)
        self.value = nn.Conv2d(in_channels, in_channels, kernel_size=1, stride=1)
        self.gamma = nn.Parameter(torch.zeros(1))
        # Gamma is an attenuation parameter generated by torch. zero, and the function of nn. Parameter is to convert it into a trainable parameter.
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, input):
        batch_size, channels, height, width = input.shape
        # input: B, C, H, W -> q: B, H * W, C // 8
        q = self.query(input).view(batch_size, -1, height * width).permute(0, 2, 1)
        # input: B, C, H, W -> k: B, C // 8, H * W
        k = self.key(input).view(batch_size, -1, height * width)
        # input: B, C, H, W -> v: B, C, H * W
        v = self.value(input).view(batch_size, -1, height * width)
        # q: B, H * W, C // 8 x k: B, C // 8, H * W -> attn_matrix: B, H * W, H * W
        attn_matrix = torch.bmm(q, k)
        attn_matrix = self.softmax(attn_matrix)
        out = torch.bmm(v, attn_matrix.permute(0, 2, 1))
        out = out.view(*input.shape)
        return self.gamma * out + input

# Custom Load Data
class SeqDataset(Dataset):  # Data Load
    def __init__(self, dataf,AC_martix,AD_martix,data_wea,data_new, inputnum):
        self.imgseqs = dataf  # read in data
        self.num_samples = self.imgseqs.shape[1]  # Number of sequence samples
        self.inputnumMin = inputnum  # Input sequence length
        self.AC_M = AC_martix
        self.AD_M = AD_martix
        self.AW_data= data_wea
        self.AN_data = data_new

    def __getitem__(self, index):
        current_index = np.random.choice(range(self.inputnumMin, self.num_samples))
        current_label = self.imgseqs[:,current_index]
        # min
        current_imgs=self.imgseqs[:,current_index-self.inputnumMin:current_index]
        current_imgs=torch.FloatTensor(current_imgs)

        #Current label value
        current_label=torch.FloatTensor(current_label)
        #Corresponding weather matrix generation
        AW_M=np.ones((Nodes_num,Nodes_num))*self.AW_data[current_index]
        AW_M[np.eye(Nodes_num,dtype=np.bool)]=0
        AW_M=normalize(torch.FloatTensor(AW_M).to(device), True)

        # Corresponding new matrix generation
        AN_M = np.ones((Nodes_num, Nodes_num)) * self.AN_M[current_index]
        AN_M[np.eye(Nodes_num, dtype=np.bool)] = 0
        AN_M = normalize(torch.FloatTensor(AN_M).to(device), True)

        return current_imgs, current_label, self.AC_M,self.AD_M,AW_M,AN_M

    def __len__(self):
        return self.imgseqs.shape[1]

class model_Net(nn.Module):
    def __init__(self,dim_in,dim_out,Nodes_num):
        super(model_Net, self).__init__()
        self.outlen = dim_out
        self.inlen = dim_in
        self.numnodes=Nodes_num
        self.fc1 = nn.Linear(1, 1, bias=True)
        self.fc2 = nn.Linear(1, 1, bias=True)
        self.fc3 = nn.Linear(1, 1, bias=True)
        self.fc4 = nn.Linear(1, 1, bias=True)

        self.selfattentiont01 = selfattention(Nodes_num)
        self.selfattentiont02 = selfattention(Nodes_num)
        self.selfattentiont03 = selfattention(Nodes_num)


        self.fc5 = nn.Linear(dim_in, dim_in, bias=True)
        self.fc6 = nn.Linear(dim_in, dim_in, bias=True)

        self.conv3d = nn.Sequential(
            nn.Conv3d(1, 1, (1, 1, 1), stride=1, padding=0),
            nn.Conv3d(1, 1, (1, 1, 1), stride=1, padding=0)
        )

        self.selfattentiont1 = selfattention(Nodes_num)
        self.selfattentiont2 = selfattention(Nodes_num)

        self.dcn2d = nn.Sequential(
            nn.Conv2d(1, 1, kernel_size=(1, 2), stride=(1, 2), padding=0, dilation=2),
            nn.Conv2d(1, 1, kernel_size=(1, 2), stride=(1, 2), padding=0, dilation=2),
            nn.Conv2d(1, 1, kernel_size=(1, 2), stride=(1, 2), padding=0, dilation=1),
        )
        self.cnn2d = nn.Sequential(
            nn.Conv2d(1, 1, kernel_size=(1, 2), stride=(1, 2), padding=0),
            nn.Conv2d(1, 1, kernel_size=(1, 2), stride=(1, 2), padding=0),
            nn.Conv2d(1, 1, kernel_size=(1, 2), stride=(1, 2), padding=0),
        )

        self.fc7 = nn.Linear(dim_out, dim_out, bias=True)


    def forward(self,X,AC0,AD0,AW0,AN0):
        Batch = X.shape[0]
        #externalities
        AC = AC0.view(Batch,self.numnodes,self.numnodes,-1)
        AD = AD0.view(Batch,self.numnodes,self.numnodes,-1)
        AW = AW0.view(Batch, self.numnodes, self.numnodes,-1)
        AN = AN0.view(Batch, self.numnodes, self.numnodes,-1)

        AFUSE = torch.sigmoid(self.fc1(AC)+self.fc2(AW)+self.fc3(AD)++self.fc4(AN))
        AFUSE = AFUSE.view(Batch, self.numnodes,self.numnodes)
        #Spatial feature extraction
        XS=X
        #XS=spatial(XS) Replace with your own spatial feature extraction module

        #Space Enhancement Simplified Edition
        XS0=X #If it's not a simplified version, read the grid features here
        XS0=XS0.view(Batch,1,self.numnodes,self.inlen)
        XSZ=XS0.permute(0,3,1,2)
        XSZ=XSZ.view(XSZ.shape[0],1,XSZ.shape[1],XSZ.shape[2],XSZ.shape[3])
        XSZ=self.conv3d(XSZ).permute(0,1,3,4,2)
        XSZ=XSZ.view(XSZ.shape[0],XSZ.shape[3],XSZ.shape[4])

        #Enhanced Fusion
        XS=XS.view(XS.shape[0],XS.shape[1],XS.shape[2],-1)
        XSZ=XSZ.view(XSZ.shape[0],XSZ.shape[1],XSZ.shape[2],-1)
        XSF=self.selfattentiont1(XS)*torch.sigmoid(self.selfattentiont2(XSZ))

        #Time-varying module
        XT=XSF.view(Batch,-1,self.numnodes,self.inlen)
        XT=self.dcn2d(XT)

        XTR = XSF.view(Batch, -1, self.numnodes, self.inlen)
        XTR=self.cnn2d(XTR)

        XT=XT+XTR
        XT=XT.view(Batch,self.numnodes,-1)
        XT=self.fc7(XT)
        out=XT.view(Batch,-1)

        return out


def train(epoch,model,timenode):
    erro=[]
    epoch_start_time=time.time()

    for batch_idx, (batch_x,batch_y,batch_ac,batch_ad,batch_aw,batch_an) in enumerate(train_loader, 0):
        inputs, label, AC, AD, AW , AN = Variable(batch_x).to(device), Variable(batch_y).to(device), \
                                    Variable(batch_ac).to(device), Variable(batch_ad).to(device), Variable(batch_aw).to(device), Variable(batch_an).to(device)
        # print(inputs.shape,inputs1.shape,label.shape)
        output = model(inputs, AC, AD, AW, AN)
        output = output.view(-1, Nodes_num, OUT_SIZE)
        label = label.view(-1, Nodes_num, OUT_SIZE)
        loss_func = nn.MSELoss()
        loss = loss_func(output, label)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        # scheduler.step(loss)
        erro.append(loss.data.cpu().numpy())
    #validate
    # model=torch.load(data_path + "best_loss.pth").to(device)
    if epoch!=0 and np.mean(erro) < np.min(loss_list):
        torch.save(model, data_path + "best_loss.pth")  # Model Save
    timenode+=1
    val_erro = []
    for batch_idx, (batch_x, batch_y, batch_ac, batch_ad, batch_aw) in enumerate(train_loader, 0):
        inputs, label, AC, AD, AW = Variable(batch_x).to(device), Variable(batch_y).to(device), \
                                                      Variable(batch_ac).to(device), Variable(batch_ad).to(
            device), Variable(batch_aw).to(device)
        # print(inputs.shape,inputs1.shape,label.shape)
        # model = torch.load('tensors.pt')
        output = model(inputs,AC, AD, AW)
        output=output.view(-1,Nodes_num,OUT_SIZE)
        label=label.view(-1,Nodes_num,OUT_SIZE)
        loss_func = nn.MSELoss()
        loss = loss_func(output, label)
        val_erro.append(loss.data.cpu().numpy())


    if epoch!=0 and np.mean(val_erro) < np.min(val_loss_list):
        torch.save(model, data_path + "best_val_loss.pth")  # Model Save
        print("Save best weights: val_loss="+str(np.mean(val_erro)))
        timenode=0

    if epoch!=0 and timenode == 20:
        for p in optimizer.param_groups:
            p['lr'] *= 0.8
        timenode=0
    print('Train Epoch:[{:03d}/{:03d}] Sec: {:.3f} Loss: {:.6f} val_Loss: {:.6f} lr: {}'.format(
        epoch, num_epoch, time.time() - epoch_start_time, np.mean(erro),np.mean(val_erro), optimizer.state_dict()['param_groups'][0]['lr']))

    if epoch % 10 == 0:
        torch.save(model, model_path +'/'+ str(epoch) +"_valloss-"+str(np.mean(val_erro))+ ".pth") #save

    loss_list.append(np.mean(erro))
    val_loss_list.append(np.mean(val_erro))

    # Draw loss curve
    plt.plot(loss_list, '.-')
    plt.xlabel('times')
    plt.ylabel('Test loss')
    data_loss = pd.DataFrame(loss_list)
    data_loss.to_csv(data_path + 'loss_data.csv')
    plt.savefig(data_path + 'loss_fig_.svg', format='svg')
    plt.clf()
    # Draw loss curve
    plt.plot(val_loss_list, '.-')
    plt.xlabel('times')
    plt.ylabel('Val loss')
    data_loss = pd.DataFrame(val_loss_list)
    data_loss.to_csv(data_path + 'val_loss_data.csv')
    plt.savefig(data_path + 'val_loss_fig_.svg', format='svg')
    plt.clf()
    return model,timenode

if __name__=='__main__':
    #Model initialization
    BATCH_SIZE = 30 #Batch size
    SEQ_SIZE = 12  # Input dimension
    OUT_SIZE = 1  #Output dimension
    learning_rate = 0.001  # Learning rate
    num_epoch=800 #Training frequency
    timeid = time.time()
    timeArray = time.localtime(timeid)
    timestart = time.strftime("%Y%m%d %H-%M-%S", timeArray)
    model_kind='RTM-GCN1'  #模型名称
    data_kind=['PEMS03[0]','PEMS04[0]','PEMS07[0]','PEMS08[0]','SZ_SPEED[0]']
    data_index=0 #Dataset sequence number
    data_id=0  #0
    type=data_kind[0][0:4]
    if type=='PEMS':
        data_interval=288
    else:
        data_interval = 96

    data_path = '../data/data_save/' +model_kind+'-'+data_kind[data_index]+'-'+str(timestart)+'/'
    model_path = data_path + 'model_pth'
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    if not os.path.exists(model_path):
        os.mkdir(model_path)

    # Load Dataset
    file = np.load('../data/source_data/' + str(data_kind[data_index]) + '/' + str(data_kind[data_index]) + '.npz',
                   allow_pickle=True)
    data1 = file['data'].T
    # PEMS03(1, 358, 26208) PEMS04(3, 307, 16992) PEMS07(1, 883, 28224)  PEMS08(3, 170, 17856) SZtaxi(156, 2976)
    data = pd.DataFrame(data1[data_id].T)
    data = data.values[:,:].T
    # PEMS03((4, 26208)) 91 days; PEMS04(4, 16992) 59 days;  PEMS07(4, 28224) 98 days; PEMS08(4, 17856) 62 days;
    print("input_size:" + str(data.shape))
    # data standardization
    data_mean = data.mean()
    data_std = data.std()
    data_B = (data - data_mean) / data_std

    day_len = int(data.shape[1] / data_interval)
    train_len = int(day_len * 0.7)
    val_len = day_len - train_len
    print("train_days:%d,test_days:%d" % (train_len, val_len))
    data_train = data_B[:, 0:train_len * data_interval]
    print("train_data_size:" + str(data_train.shape))
    data_test = data_B[:, train_len * data_interval - SEQ_SIZE:day_len * data_interval]
    print("test_data_size:" + str(data_test.shape))
    Nodes_num = data_train.shape[0]
    print("Node_nums:" + str(Nodes_num))

    #Code copy
    shutil.copy(model_kind + ".py", data_path)
    #GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    #Adjacency matrix loading
    AC_martix = pd.read_csv(
        '../data/data_martix/' + data_kind[data_index] + '/data_corr.csv', header=0,
        index_col=0)
    AC_martix = AC_martix.values
    AC_martix = normalize(torch.FloatTensor(AC_martix).to(device), True)
    AD_martix = pd.read_csv(
        '../data/data_martix/' + data_kind[data_index] + '/data_dist.csv', header=0,
        index_col=0)
    AD_martix = AD_martix.values
    AD_martix = normalize(torch.FloatTensor(AD_martix).to(device), True)
    data_wea = pd.read_csv('../data/data_martix/' + data_kind[data_index]  + '/data_wea.csv',
                           header=0, index_col=0).values
    data_new = pd.read_csv('../data/data_martix/' + data_kind[data_index] + '/data_new.csv',
                           header=0, index_col=0).values

    train_data = SeqDataset(data_train, AC_martix, AD_martix, data_wea,data_new, inputnum=SEQ_SIZE)
    train_loader = DataLoader(train_data, shuffle=True, batch_size=BATCH_SIZE)
    val_data = SeqDataset(data_test, AC_martix, AD_martix, data_wea,data_new, inputnum=SEQ_SIZE)
    val_loader = DataLoader(val_data, shuffle=True, batch_size=1)
    model = model_Net(SEQ_SIZE, OUT_SIZE, Nodes_num)
    model = model.to(device)
    # Initialize optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min')
    loss_list = []
    val_loss_list = []
    print("----model--training---- ")
    timenode = 0
    for epoch in range(num_epoch):
        model, timenode = train(epoch, model, timenode)
    print("----model--train---End---- ")






