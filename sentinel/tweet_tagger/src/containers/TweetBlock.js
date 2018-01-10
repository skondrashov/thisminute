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
  constructor(props) {
    super(props);
  }

  render() {
  	const { connectDragSource, isDragging } = this.props;
    return connectDragSource(
      <div className="tweet-block" style={{
        opacity: isDragging ? 0.5 : 1,
        cursor: 'move'
      }}>
        This is a TweetBlock
      </div>
    );
  }
}

export default DragSource('tweet', tweetSource, collect)(TweetBlock);
