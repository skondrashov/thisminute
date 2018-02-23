import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import { DropTarget } from 'react-dnd';

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
