import React, { Component } from 'react';
import { DragSource } from 'react-dnd';

const Types = {
  TWEETBLOCK: 'tweetBlock'
};

const tweetSource = {
  beginDrag(props) {
    return {};
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
      const post_id = tweet.post_id;

      return(
        <div key={post_id}>
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
