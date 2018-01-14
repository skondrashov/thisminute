import React, { Component } from 'react';
import TweetBlock, { Types } from './TweetBlock';
import { DropTarget, DragDropContext } from 'react-dnd';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import { dropInCategory } from '../actions/index';

const tweetTarget = {
  drop(props, monitor) {
    return { category: props.categoryName }
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
      tweets: [
        {username: "user1", content: "content1", post_id: "1"},
        {username: "user2", content: "content2", post_id: "2"}
      ]
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
      return <TweetBlock key={tweet.post_id} tweet={tweet} />;
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

function mapDispatchToProps(dispatch) {
  return bindActionCreators({ dropInCategory }, dispatch);
}

CategoryBlock = DropTarget('tweet', tweetTarget, collect)(CategoryBlock);
CategoryBlock = connect(null, mapDispatchToProps)(CategoryBlock);
export default CategoryBlock;
