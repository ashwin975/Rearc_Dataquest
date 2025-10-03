
Performed data analysis and answered questions 

**Source Code** : [population.ipynb](/part3-data-analysis/population.ipynb)

**Question 1** : Calculated US population summary (2013-2018)
 - Mean : 317437383.0
 - Standard Deviation : 4257089.54

**Question 2** : Best Year by Series ID
- Parsed `pr.data.0.Current` into a dataframe
- Grouped data by Series ID and Year and calculated sum of values
- Identified best year for each Series ID

**Question 3** : Population mapping for specified series and period
- Filtered `pr.data.0.Current` for series_id = PRS30006032 and period = Q01
- Right merge population dataset on year column
  
