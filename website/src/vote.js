/* globals tm */
import React, { Component } from 'react';
import $ from 'jquery';

$(document).on("mouseover", ".vote>div", function() {
	let $el = $(this);
	for (let sentiment of tm.sentiments) {
		if ($el.parent().hasClass(sentiment.key)) {
			console.log($('.infobox .description .' + sentiment.key));
			$('.infobox .description .' + sentiment.key).children($el.hasClass('up') ? '.up' : '.down').show();
		}
	}
});

$(document).on("mouseout", ".vote>div", function() {
	$('.infobox .description').children().children().hide();
});

const sentiments = tm.sentiments.map(sentiment =>
	<div key={sentiment.key} className={`${sentiment.key} vote vote-only hidden`}>
		<div className="up"></div>
		<div className="down"></div>
	</div>
);


export default class Vote extends Component {
	constructor(props) {
		super(props);

		this.state = {
			sentiments: sentiments,
		};
	}

	render() {
		return (
			<>
				{this.state.sentiments}
			</>
		);
	}
}
