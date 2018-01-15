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

  renderOverlay(color) {
    return(
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        height: '100%',
        width: '100%',
        zIndex: 1,
        opacity: 0.5,
        backgroundColor: color
      }} />
    );
  }

  renderTweetBlocks() {
    return this.state.tweets.map((tweet) => {
      const t = {};
      /*for each (stateTweet in state.tweets) {
        if(stateTweet.post_id == tweet.id) {
          console.log(stateTweet);
          t = stateTweet;
        }
      }*/
      return <TweetBlock key={tweet.tweet_id} tweet={tweet} />;
    });
  }

  render() {
    const { connectDropTarget, isOver, canDrop } = this.props;

    return connectDropTarget(
      <div className="grid category-list" style={{
        position: 'relative',
        width: '100%',
        height: '100%'
      }}>
        <div className="text-center">
          <h3>{this.props.categoryName}</h3>
        </div>
        {this.renderTweetBlocks()}
        {isOver && canDrop && this.renderOverlay('yellow')}
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
