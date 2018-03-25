from __future__ import print_function
from __future__ import division
import sys, os
sys.path.append(os.path.abspath('/srv/lib/'))

import Model

from tensorflow.contrib.tensor_forest.client import random_forest
from tensorflow.contrib.tensor_forest.python import tensor_forest

from tensorflow.python.estimator.inputs import numpy_io

class Random_Forest(Model):
	def load(self, path):
		random_forest.TensorForestEstimator(
				tensor_forest.ForestHParams(
						num_classes=2,
						num_features=784,
						num_trees=100,
						max_nodes=1000
					),
				graph_builder_class=tensor_forest.RandomForestGraphs if True else tensor_forest.TrainingLossForest,
				model_dir=path
			)

		self.rf = model.fit(
				input_fn=numpy_io.numpy_input_fn(
					x={'features': Model.Xs[self.dataset]},
					y=Model.Ys[self.dataset],
					batch_size=1000,
					num_epochs=None,
					shuffle=True
				),
				steps=None
			)

	def predict(self, X):
		return self.rf.predict(
				input_fn=numpy_io.numpy_input_fn(
					x={'features': X},
					batch_size=1000,
					num_epochs=1,
					shuffle=False
				)
			)