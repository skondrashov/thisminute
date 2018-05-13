from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from model import Model
from util import config

from sklearn.externals import joblib
from sklearn.ensemble import RandomForestClassifier

class Random_Forest(Model):
	def load(self):
		self.rf = joblib.load(self.path)

	def train(self, X, Y):
		rf = RandomForestClassifier(
				n_jobs=config('pericog', 'thread_count'),

				n_estimators=5000, # number of trees
				criterion='gini', # 'gini' or 'entropy'

				verbose=1,

				max_features='sqrt', # 'sqrt', 'log2', or a percentage of the total features for each forest to consider

				class_weight=None,

				max_depth=None,
				min_samples_split=2,
				min_samples_leaf=1,
				min_weight_fraction_leaf=0.0,
				max_leaf_nodes=None,
				min_impurity_decrease=0.0,

				bootstrap=True,
				oob_score=False,
				random_state=None,
				warm_start=False,
			)
		rf.fit(X, Y)
		joblib.dump(rf, self.path)

	def predict(self, X):
		X, Y = self.input_fn(X, [])
		return self.rf.predict(X)
