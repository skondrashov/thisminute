import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import { DropTarget } from 'react-dnd';
import { connect } from 'react-redux';

const tweetTarget = {
  drop(props, monitor) {
    return { category: props.categoryName };
  }
};

function collect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    canDrop: monitor.canDrop()
  };
}

class CategoryBlock extends Component {

  renderTweetBlocks() {
    return this.props.tweets.map((tweet) => {
      return <TweetBlock key={tweet.tweet_id} tweet={tweet} />;
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
        {this.renderTweetBlocks()}
      </div>
    );
  }
}

function mapStateToProps(state) {
  console.log(state.CategoryBlockReducer.categoryBlockTweets);
  return { tweets: state.CategoryBlockReducer.categoryBlockTweets };
}

CategoryBlock = DropTarget('tweet', tweetTarget, collect)(CategoryBlock);
CategoryBlock = connect(mapStateToProps)(CategoryBlock);
export default CategoryBlock;
