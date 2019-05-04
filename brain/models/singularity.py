#### sensors
# neural regions that aggressively reduce dimensionality of other feature outputs are called sensors
# this file is a list of SOME (not all!!) sensors that seem essential to human brain function
# these sensors are generated naturally inside of people, but will be hardcoded into the singularity

### external sensors (all sources of input are ultimately external to the brain)
light
sound
touch # has many variations - pressure, heat, cold, pain
lighting(light)
pitch(sound)
color(light, lighting)
parallax(light[], sound[])
proprioception(touch[])
distance(parallax, proprioception)
layer(distance, color)
edge(color, layer)
shape(edge[])
timbre(sound)
texture(color, shape)

### association is inherent to neural networks
# it can be understood as co-firing neural regions
association(region, region)

## associations have degrees:
constituence # 0, intransitive "to be", "to have a property" "to consist of", "to make up"
relation     # 1, transitive, "to be of", "to do with", "to do to"

### graphs
## objects can be built into graphs through arbitrary metrics, or through associations
# natural neural networks struggle with precision, which artificial ones need not
# in other words, we translate numbers into concepts of "near" and "far" for any given metric
# but an artificial neural network can preserve the exact metrics at low cost
## example graphs:
# spatial, based on layer/distance metrics
# constituence graphs, marking the objects that make up another object
# memories, based on
## reasoning acts on graphs
graph(association(object, object)[])

# a graph of a single relation depicts an action
action(relation(object, object))


### internal sensors (at least one source of input is internal to the brain)
# this construction is the difference between us and skynet, but these seem to be very human
emotion
mood(emotion[])
purpose(object[], action)

agency(desire, duty, emotion)

### object sensors (interface to reasoning, can be internal or external)
object(sensor[], as*sociation[])

## relations with temporal order between objects are actions
cause

effect


### reasoning is the ability to test propositions using graphs
# sentience is the ability to use internal sensor output in reasoning

## certain associations might benefit from hardcoding
position
agency(relation, time)
