import pandas as pd

allSongs = pd.read_csv('mainSongs.csv')

group_size = 1000

lst = [allSongs.iloc[i:i+group_size] for i in range(0,len(allSongs),group_size)]

for i in range(len(lst)):
    lst[i].to_csv('mainSongs'+str(i)+'.csv', index=False)

print('Done')

