import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import { DropTarget } from 'react-dnd';

const tweetTarget = {
  drop(props) {
    return {};
  }
};

function collect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    isOver: monitor.isOver()
  };
}

class CategoryBlock extends Component {
  render() {
    const { x, y, connectDropTarget, isOver } = this.props;
    return connectDropTarget(
      <div className="grid category-list">
        <div className="text-center">
          {isOver &&
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              height: '100%',
              width: '100%',
              zIndex: 1,
              opacity: 0.5,
              backgroundColor: 'yellow',
            }} />
          }
          <h3>Category Name</h3>
        </div>
        <div className="">
          <TweetBlock />
        </div>
        <div className="">
          <TweetBlock />
        </div>
      </div>
    );
  }
}

export default DropTarget('tweet', tweetTarget, collect)(CategoryBlock);
