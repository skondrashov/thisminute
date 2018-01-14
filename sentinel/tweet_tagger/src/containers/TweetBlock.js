import React, { Component } from 'react';
import { DragSource } from 'react-dnd';
import { dropInCategory } from '../actions/index';

const Types = {
  TWEETBLOCK: 'tweetBlock'
};

const tweetSource = {
  beginDrag(props) {
    return { post_id: props.tweet.post_id };
  },

  endDrag(props, monitor, component) {
    if(!monitor.didDrop()) {
      console.log('didnt drop');
      return;
    }
    const tweet = monitor.getItem();
    const dropAt = monitor.getDropResult();
    dropInCategory(tweet.post_id, dropAt.category);
  }
};

function collect(connect, monitor) {
  return {
    connectDragSource: connect.dragSource(),
    isDragging: monitor.isDragging(),
  }
}

class TweetBlock extends Component {

  renderContent(tweet) {
    if(tweet) {
      const username = tweet.username;
      const content = tweet.content;

      return(
        <div>
          <div><b>{content}</b></div>
          <small>{username}</small>
        </div>
      );
    }
  }

  render() {
    const { connectDragSource, isDragging } = this.props;

    return connectDragSource(
      <div
        className="tweet-block"
        style={{
          opacity: isDragging ? 0.5 : 1,
          cursor: 'move'
      }}>
        {this.renderContent(this.props.tweet)}
      </div>
    );
  }
}

TweetBlock = DragSource('tweet', tweetSource, collect)(TweetBlock);
export default TweetBlock;
