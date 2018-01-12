import React, { Component } from 'react';
import CategoryBlock from './CategoryBlock';

class CategoryList extends Component {
  constructor(props) {
    super(props);

    this.state = {
      categories: [
        "Category 1",
        "Category 2",
        "Category 3"
      ]
    }
  }

  renderCategoryBlocks() {
    return this.state.categories.map((category) => {
      return <CategoryBlock key={category} category={category} />;
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
