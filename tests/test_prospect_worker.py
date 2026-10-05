import unittest
from workers.prospect_worker import validate_result
class T(unittest.TestCase):
 def setUp(self): self.p={"offers":[{"name":"A"},{"name":"B"}]}
 def v(self): return {"decision":"QUALIFIED","confidence":90,"problem":"x","buyer_type":"y","matched_offer":"A","priority":80,"evidence":["x"],"missing_information":["z"],"reason":"x","next_validation":"x"}
 def test_valid(self): validate_result(self.v(),self.p)
 def test_bad_offer(self):
  r=self.v(); r["matched_offer"]="C"
  with self.assertRaises(ValueError): validate_result(r,self.p)
 def test_missing_offer(self):
  r=self.v(); r["matched_offer"]=None
  with self.assertRaises(ValueError): validate_result(r,self.p)
if __name__=="__main__": unittest.main()