import React, { Component } from 'react';
import CategoryBlock from './CategoryBlock';

class CategoryList extends Component {
  constructor(props) {
    super(props);

    this.state = {
      categories: [
        "Not Relevant",
        "Thoughts/Prayers",
        "Eyewitness"
      ]
    }
  }

  renderCategoryBlocks() {
    return this.state.categories.map((category) => {
      return <CategoryBlock key={category} categoryName={category} />;
    });
  }

  render() {
    return (
      <div className="category-block">
        {this.renderCategoryBlocks()}
      </div>
    );
  }
}

export default CategoryList;
