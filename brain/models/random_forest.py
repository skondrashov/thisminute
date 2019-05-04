from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

from util import config
from model import Model

from sklearn.externals import joblib
from sklearn.ensemble import RandomForestClassifier

class random_forest(Model):
	def load(self):
		self.random_forest = joblib.load(self.path)

	def train(self, X, Y):
		random_forest = RandomForestClassifier(
				n_jobs=config('pericog', 'thread_count'),

				n_estimators=100, # number of trees
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
		random_forest.fit(X, Y)
		joblib.dump(random_forest, self.path)

	def predict(self, X):
		X, Y = self.input_function(X, [])
		return self.random_forest.predict(X)
