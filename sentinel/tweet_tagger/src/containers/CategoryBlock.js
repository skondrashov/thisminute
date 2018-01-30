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
    isOver: monitor.isOver(),
    canDrop: monitor.canDrop()
  };
}

class CategoryBlock extends Component {
  constructor(props) {
    super(props);

    this.state = {
      categoryName: "",
      tweets: []
    }
  }

  renderTweetBlocks() {
    return this.state.tweets.map((tweet) => {
      return <TweetBlock key={tweet.tweet_id} tweet={tweet} />;
    });
  }

  render() {
    const { connectDropTarget, isOver, canDrop } = this.props;

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
  return { tweets: state.tweets };
}

CategoryBlock = DropTarget('tweet', tweetTarget, collect)(CategoryBlock);
CategoryBlock = connect(mapStateToProps)(CategoryBlock);
export default CategoryBlock;
