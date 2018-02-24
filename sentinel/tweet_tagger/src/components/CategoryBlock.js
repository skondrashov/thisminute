import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import { DropTarget } from 'react-dnd';

/* State for CategoryBlocks are stored in the parent component CategoryList.
react-dnd library puts a component wrapper around DropTargets (like CategoryBlock),
and that DropTarget wrapper component is the one that recieves data from the
DragSource (TweetBlocks). The DropTarget wrapper component has access to a
CategoryBlock's props, but not its state, so data from a DropSource must be sent
upward through a function in a CategoryBlock's props and then sent back downward
as a prop from the parent component CategoryList.
https://github.com/react-dnd/react-dnd/issues/349 */

const tweetTarget = {
  drop(props, monitor) {
    const tweet = monitor.getItem();
    props._addTweetToCategory(tweet, props.categoryId);
  }
};

function collect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    canDrop: monitor.canDrop()
  };
}

class CategoryBlock extends Component {

  _renderTweetBlocks() {
    return this.props.tweets.map((tweet) => {
      return (
        <TweetBlock
          key={tweet.id}
          tweet={tweet}
        />
      );
    });
  }

  render() {
    const { connectDropTarget, canDrop } = this.props;

    return connectDropTarget(
      <div
        className="grid category-list"
        style={{
          opacity: canDrop ? 0.5 : 1,
          backgroundColor: canDrop ? 'yellow' : ''
      }}>
        <div className="text-center">
          <h3>{this.props.categoryName}</h3>
        </div>
        {this._renderTweetBlocks()}
      </div>
    );
  }
}

CategoryBlock = DropTarget('tweet', tweetTarget, collect)(CategoryBlock);
export default CategoryBlock;
