import React, { Component } from 'react';
import { DragSource } from 'react-dnd';

const tweetSource = {
  beginDrag(props) {
    return { tweet: props.tweet };
  },

  endDrag(props, monitor, component) {
    if(!monitor.didDrop()) {
      console.log('invalid drop target');
      return;
    }
    const tweet = monitor.getItem().tweet;
    if(props._removeFromTweetList) {
      props._removeFromTweetList(tweet);
    }
    if(props._removeFromCategoryBlock) {
      props._removeFromCategoryBlock(tweet.id);
    }
  }
};

function collect(connect, monitor) {
  return {
    connectDragSource: connect.dragSource(),
    isDragging: monitor.isDragging(),
  }
}

class TweetBlock extends Component {
  render() {
    const { connectDragSource, isDragging } = this.props;

    return connectDragSource(
      <div
        className="tweet-block"
        style={{
          opacity: isDragging ? 0.5 : 1,
          cursor: 'move'
      }}>
        {this.props.tweet.content}
      </div>
    );
  }
}

TweetBlock = DragSource('tweet', tweetSource, collect)(TweetBlock);
export default TweetBlock;
