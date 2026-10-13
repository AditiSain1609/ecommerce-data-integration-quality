import pandas as pd
from src.quality_checks import assess, score, duplicate_mask

def test_scores_and_empty_denominator():
    assert score(1,2)==50 and score(0,0)==100

def test_completeness_and_duplicate_detection():
    frame=pd.DataFrame([{"id":1,"email":"a"},{"id":1,"email":None}])
    result=assess(frame,["id","email"],["id"])
    assert result["invalid"]==1 and result["duplicates"]==1

def test_duplicate_business_key():
    assert duplicate_mask(pd.DataFrame({"id":[1,1]}),["id"]).sum()==1
