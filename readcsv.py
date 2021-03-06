import pandas as pd
import numpy as np  
from queue import PriorityQueue
import json
import statsmodels.api as sm
import statsmodels.formula.api as smf

try:
    import psycopg2
    con = psycopg2.connect(host = 'pgdb12.iri.columbia.edu',
        database = 'DesignEngine',
        user = 'fist',
        password = 'MonellIRI')
except:
    pass

DataStore = None
# dataFrame = pd.read_sql("select * from bad1years_drought_ethiopia_compiled_forms", con)

def writeLog(typ, time, data):
    cursor = con.cursor()
    cursor.execute("INSERT INTO  clean_log (id, type, time, data ) VALUES(DEFAULT,%s, %s, %s)", (typ, time, data)) 
    con.commit()

def readLog():
    df = pd.read_sql("select * from clean_log", con) 
    arr = []
    for index, row in df.iterrows():
        try:
            # print(row['data'])
            arr.append(json.loads(row['data']))
        except Exception as e:
            print(e)
            continue
    # print(arr)
    return arr

def readsub():
    df = pd.read_sql("select * from clean_log", con) 
    arr = []
    for index, row in df.iterrows():
        if(row['type']!= 'submission'):
            continue
        try:
            # print(row['data'])
            arr.append(json.loads(row['data']))
        except Exception as e:
            print(e)
            continue
    # print(arr)
    return arr

class HierachyData():
    # filename is the file to be read 
    # hiearchy is a list of hiearchy attributes in descending order
    def __init__(self, filename, hiearchy):
        if(filename.startswith("./")):
            self.data = pd.read_csv(filename)
        else:
            self.data = pd.read_sql("select * from " + filename, con)
        for attr in hiearchy:
            if attr not in self.data.columns:
                self.data[attr] = ""
        print(self.data)
        global DataStore
        DataStore  = self.data.copy()
        self.data = self.data.set_index(hiearchy)
        self.hiearchy = hiearchy

    def get_summary2(self):
        self.summary = self.data.reset_index()[self.hiearchy[0:4]].groupby(self.hiearchy[0:3]).agg(['unique']).to_json(orient='index')
        return self.summary

    def get_summary(self):
        self.summary = self.data.reset_index()[self.hiearchy[0:2]].groupby(self.hiearchy[0]).agg(['unique']).to_json(orient='index')
        return self.summary

    # get unique for header
    def get_unique(self,hierchy_values):
        if len(hierchy_values) == 0:
            return self.data.reset_index()[self.hiearchy[len(hierchy_values)]].unique().tolist()
        return self.data.loc[tuple(hierchy_values)].reset_index()[self.hiearchy[len(hierchy_values)]].unique().tolist()

    # get data given hierchy_values
    def get_data(self,hierchy_values):
        return self.data.loc[tuple(hierchy_values)].reset_index().to_json(orient='records')  

    # get data given hierchy_values
    def get_data2(self,set_values):
        result = None
        print(set_values)
        for value in set_values:
            try:
                if(result is None):
                    result = self.data.loc[value]
                else:
                    result = result.append(self.data.loc[value])
            except: 
                pass
        result["rank"] = result.groupby("Village")["value"].rank(ascending=True,method='first')
        # result.groupby(categorical[0]).rank(ascending=False,method='first') 
        return result.reset_index().to_json(orient='records')  


    # get data given hierchy_values
    # list of two categorical attributes
    # one numerical attribute
    # and aggragation method
    def get_heatmap_data(self,hierchy_values,categorical,numerical,aggragation):
        
        return self.get_heatmap(hierchy_values,categorical,numerical,aggragation).to_json(orient='records')
        # return self.data.loc[tuple(hierchy_values)].groupby(categorical).agg(aggragation).reset_index().to_json(orient='records')   

    def get_heatmap_withtotal(self,hierchy_values,categorical,numerical,aggragation):
        # return self.data.loc[tuple(hierchy_values)][categorical+numerical]\
        #              .groupby(categorical)[numerical].agg(aggragation).reset_index().to_json(orient='records')   
        aggregation = ['mean','std','count']
        
        if len(hierchy_values) == 0:
            agg = self.data
        else:
            agg = self.data.loc[tuple(hierchy_values)]
        agg = agg.groupby(categorical[-1])[numerical].agg(aggregation)
        agg = agg.replace(np.nan, 0)
   
        # print(agg)
        agg.columns = ['mean','std','count']
        agg[categorical[0]] = 'total'
        # agg["rank"]  = (agg["mean"]*agg["count"]).rank(ascending=True)
        agg["rank"]  = (agg["mean"]*agg["count"]).rank(ascending=False,method='first')
        if len(hierchy_values) == 0:
            each = self.data
        else:
            each = self.data.loc[tuple(hierchy_values)]
        each = each.groupby(categorical)[numerical].agg(aggregation)
        # print(each)
        each.columns = ['mean','std','count']
        each = each.replace(np.nan, 0)
        each["rank"]  = (each["mean"]*each["count"]).groupby(categorical[0]).rank(ascending=False,method='first') 
        # print(each)
        return pd.concat([agg.reset_index(),each.reset_index()])

    def get_heatmap(self,hierchy_values,categorical,numerical,aggragation):
        aggregation = ['mean','std','count']

        if len(hierchy_values) == 0:
            each = self.data
        else:
            each = self.data.loc[tuple(hierchy_values)]
        each = each.groupby(categorical)[numerical].agg(aggregation)
        # print(each)
        each.columns = ['mean','std','count']
        each = each.replace(np.nan, 0)
        each["rank"]  = (each["mean"]*each["count"]).groupby(categorical[0]).rank(ascending=False,method='first') 
        # print(each)
        # if sid, also include cause
        print(categorical)
        
        if(categorical[0] == 'sid'):
            each = each.reset_index()
            # print(each)
            # print(self.data.reset_index()[["sid", "cause"]])
            each = each.merge(self.data.reset_index()[["sid","year", "cause"]])
            print(each)

            return each
        
        return each.reset_index()

    def get_heatmap_withoutagg(self,hierchy_values,categorical,numerical,aggragation):
        # return self.data.loc[tuple(hierchy_values)][categorical+numerical]\
        #              .groupby(categorical)[numerical].agg(aggragation).reset_index().to_json(orient='records')   
        aggregation = ['mean','std','count']
        each = self.data.loc[tuple(hierchy_values)].groupby(categorical).agg(aggregation)
        # print(each)
        each.columns = ['mean','std','count']
        each["rank"]  = (each["mean"]/each["count"]).groupby(categorical[0]).rank(ascending=True) 
        # print(each)
        return each.reset_index()
    
    def complaint(self,hierchy_values,categorical,numerical,aggragation,year,de_mean):
        df_all = self.get_heatmap_withoutagg(hierchy_values,categorical,numerical,aggragation)
        # print(df_all)
        df_all = df_all.replace(np.nan, 0)
        # print(df_all)
        all_mean = df_all['mean'].median()
        all_count = df_all['count'].median() 
        df = df_all[df_all.year == year]
        year_mean = df['mean'].median()
        year_count = df['count'].median()
        # print(df)
        total_count = df['count'].sum()
        total = (df['count']*df['mean']).sum()
        cur_mean = total/total_count
        q = PriorityQueue()
        cur_dif = abs(de_mean - cur_mean)
        # print(cur_mean)
        # print(df.size)
        for i in range(df.shape[0]):
            
            geo = df[categorical[0]].iloc[i]
            
            count = df['count'].iloc[i]
            mean = df['mean'].iloc[i]
            
            # if there is 0 record, where mean == nan
            if(mean != mean):
                oldsum = 0
            else:
                oldsum = count*mean

            geo_data = df_all[df_all[categorical[0]]==geo].median()
            geo_mean = geo_data['mean']
            geo_count = geo_data['count']
            est_mean = geo_mean + year_mean - all_mean
            
            # new_mean = (total - mean*count + est_mean*count)/total_count
            # q.put((abs(de_mean - new_mean),geo, 'mean',est_mean))
            est_count = geo_count + year_count - all_count
            # new_mean = (total - mean*count + mean*est_count)/(total_count - count + est_count)
            # q.put((abs(de_mean - new_mean),geo, 'count',est_count))
            newsum = est_mean*est_count
            if(total_count - count + est_count == 0):
                new_mean = 10
            else:
                new_mean = (total - oldsum + newsum)/(total_count - count + est_count)
            if(cur_dif > abs(de_mean - new_mean)):
                q.put((abs(de_mean - new_mean),geo, est_mean ,est_count))

            # print(geo,count,mean,est_mean,est_count,new_mean )
        result = []
        top = 4
        while not q.empty() and (top > 0):
            result.append(q.get())
            top -= 1
        return result

    # categorize an attribute
    # e.g., categorize year so that return NA for all missing years
    def categorize_attribute(self, att):
        
        self.data[att] = pd.Categorical(self.data[att]) 

        


def getRegionExplanation(region, year, aggOriginal, complained_agg, com_too_small):
    RegionData = DataStore.copy()
    aggs = ["count","std","mean"]
    RegionData["year"] = pd.Categorical(RegionData["year"] ) 
    RegionData["region"] = pd.Categorical(RegionData["region"] ) 
    RegionData["district"] = pd.Categorical(RegionData["district"] ) 


    aggg = RegionData.groupby(["region","year","district"])["rank"].agg(["count","std","mean"])
    aggg = aggg.fillna(0)

    explanations = []
    
    selected = aggg.loc[(region,year)]
    pmean = selected["mean"].mean()
    pstd = selected["std"].mean()
    pcount = selected["count"].mean()

    for index, row in selected.iterrows():
        aggOld = {}
        aggNew = {}
        for agg in aggs:
            aggOld[agg] = row[agg]
        aggNew= {'mean': pmean, 'std': pstd, 'count': pcount}

        # introuce a mean 0 with count doesn't help
        if(not com_too_small and complained_agg == 'mean' and aggOld['count'] == 0 and (aggNew['count'] < 1 or aggNew['mean'] < 1 )):
            continue
        print(aggOld)
        print(aggNew)
        aggAfterRepair = add(remove(aggOriginal,aggOld),aggNew)
        
        print(aggAfterRepair)
        if((com_too_small and aggAfterRepair[complained_agg] > aggOriginal[complained_agg] + 0.01) or
         (not com_too_small and aggAfterRepair[complained_agg] < aggOriginal[complained_agg] - 0.01)) :
            
            explanation = {}
            print(row)
            explanation["district"] = row.name
            explanation["year"] = year
            explanation["aggNew"] = aggNew
            explanation["after"] = aggAfterRepair[complained_agg]
            explanations.append(explanation)
                
    
    if com_too_small:
        explanations.sort(key=lambda x: -x["after"])
    else:
        explanations.sort(key=lambda x: x["after"])
    
    return explanations[:5]
        

def getDistrictExplanation(district, year, aggOriginal, complained_agg, com_too_small):
    RegionData = DataStore[DataStore['district']==district].copy()
    aggs = ["count","std","mean"]
    RegionData["year"] = pd.Categorical(RegionData["year"] ) 
    RegionData["district"] = pd.Categorical(RegionData["district"] ) 
    RegionData["village"] = pd.Categorical(RegionData["village"] ) 


    aggg = RegionData.groupby(["district","year","village"])["rank"].agg(["count","std","mean"])
    aggg = aggg.fillna(0)

    explanations = []
    
    selected = aggg.loc[(district,year)]
    pmean = selected["mean"].mean()
    pstd = selected["std"].mean()
    pcount = selected["count"].mean()

    for index, row in selected.iterrows():
        aggOld = {}
        aggNew = {}
        for agg in aggs:
            aggOld[agg] = row[agg]
        aggNew= {'mean': pmean, 'std': pstd, 'count': pcount}
        
        aggAfterRepair = add(remove(aggOriginal,aggOld),aggNew)
        
        if((com_too_small and aggAfterRepair[complained_agg] > aggOriginal[complained_agg] + 0.01) or
         (not com_too_small and aggAfterRepair[complained_agg] < aggOriginal[complained_agg] - 0.01)) :

            explanation = {}
            explanation["village"] = row.name
            explanation["year"] = year
            explanation["aggNew"] = aggNew
            explanation["after"] = aggAfterRepair[complained_agg]
            explanations.append(explanation)
                
    
    if com_too_small:
        explanations.sort(key=lambda x: -x["after"])
    else:
        explanations.sort(key=lambda x: x["after"])
    
    return explanations[:5]


def add(agg1, agg2):
    agg3 = {}
    agg3["count"] = agg1["count"] + agg2["count"]
    if(agg3["count"] == 0):
        agg3["mean"] = 0
        agg3["std"] = 0
        return agg3
    agg3["mean"] = (agg1["count"] * agg1["mean"] + agg2["count"] * agg2["mean"])/agg3["count"]

    if(agg3["count"] == 1):
        agg3["std"] = 0
        return agg3

    var = ((agg1["count"] - 1) * (agg1["std"]**2) + (agg2["count"] - 1) * (agg2["std"]**2)
                    + agg1["count"] * ((agg1["mean"] -  agg3["mean"]) **2)
                    + agg2["count"] * ((agg2["mean"] -  agg3["mean"]) **2) )/(agg3["count"] - 1)
    if(var < 0):
        var = 0
    agg3["std"] = var**(0.5)
    return agg3

def remove(agg1, agg2):
    agg3 = {}
    agg3["count"] = agg1["count"] - agg2["count"]
    
    if(agg3["count"] == 0):
        agg3["mean"] = 0
        agg3["std"] = 0
        return agg3
    
    agg3["mean"] = (agg1["count"] * agg1["mean"] - agg2["count"] * agg2["mean"])/agg3["count"]
    
    if(agg3["count"] == 1):
        agg3["std"] = 0
        return agg3
        
    var = ((agg1["count"] - 1) * (agg1["std"]**2) - (agg2["count"] - 1) * (agg2["std"]**2)
                    + agg1["count"] * ((agg1["mean"] -  agg3["mean"]) **2)
                    - agg2["count"] * ((agg2["mean"] -  agg3["mean"]) **2) )/(agg3["count"] - 1)
    if(var < 0):
        var = 0
    agg3["std"] = var**(0.5)
    return agg3

# d = HierachyData("./db/heatmap_data_lineage.csv",['Region','District','Village','_index'])
# d.categorize_attribute('year')
# print(d.get_heatmap_data(['Tigray','Medebay-Zana','Adibearj'],['_index','year'],['rank'],'mean'))
# print(d.get_heatmap_data(['Amhara'],['_index','year'],['rank'],'mean'))

# print(d.get_summary())

# import readcsv

# d = HierachyData("./db/heatmap_data_lineage.csv",['Region','District','Village','_index'])
# d.categorize_attribute('year')
# q = d.complaint(["Amhara"],["District", "year"],['rank'],'mean',1983,2)
# print(q)
# d.get_heatmap_withoutagg(["Tigray", "Medebay-Zana"],[ "Village", "year"],['rank'],'mean')

# d = HierachyData("./db/intitiate_cleaned2.csv",['Region','District','Village','_index'])
# df = pd.read_csv("./db/intitiate_cleaned2.csv")
# print(d.get_data(['Tigray','Medebay-Zana','Adibearj']))

# d = HierachyData("./db/enactsmean.csv",['year','gid'])
# print(d.get_data([1997]))

# df = HierachyData("./db/enactsr.csv",['Region','District'])  
# df.categorize_attribute('year') 

# df.get_heatmap_data(['Amhara'],['District','year'],['rank'],'mean')

# d = HierachyData("db/0-SubregionYearRanksEarlyARC.csv",['Village'])
# print(d.get_data2(['AbaBikila','Ziha']))  
