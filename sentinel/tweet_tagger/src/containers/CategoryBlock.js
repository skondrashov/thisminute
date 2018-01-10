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
      tweets: ["<div><TweetBlock /></div>","<div><TweetBlock /></div>"]
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

  renderTweetBlock(i) {
    return(
      <div>{i}<TweetBlock /></div>
    );
  }

  render() {
    const { connectDropTarget, isOver, canDrop } = this.props;
    const tweetBlocks = [];
    console.log(this.props.tweets);
    for(let i=0; i < 2; i++) {
      tweetBlocks.push(this.renderTweetBlock(i));
    }
    return connectDropTarget(
      <div className="grid category-list">
        <div className="text-center">
          {isOver && canDrop && this.renderOverlay('yellow')}
          {isOver && !canDrop && this.renderOverlay('red')}
          <h3>Category Name</h3>
        </div>
        {tweetBlocks}
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
