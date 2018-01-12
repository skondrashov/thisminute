import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import { DropTarget, DragDropContext } from 'react-dnd';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import { dropInCategory } from '../actions/index';

const tweetTarget = {
  drop(props) {
    return {};
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
      return <TweetBlock tweet={tweet} />;
    });
  }

  render() {
    const { connectDropTarget, isOver, canDrop } = this.props;

    return connectDropTarget(
      <div className="grid category-list">
        <div className="text-center">
          {isOver && canDrop && this.renderOverlay('yellow')}
          {isOver && !canDrop && this.renderOverlay('red')}
          <h3>{this.props.category}</h3>
        </div>
        {this.renderTweetBlocks()}
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
