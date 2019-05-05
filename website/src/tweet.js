/* globals tm, google */
import React, { Component } from 'react';

import Votes from './votes';

export default class extends Component {
	constructor(props) {
		super(props);

		this.state = {
			id: props.id,
			marker: new google.maps.Marker({
				position: {lat: parseFloat(props.lat), lng: parseFloat(props.lng)},
				map: tm.map,
				icon: tm.highlighted_icon,
			}),
			votes: {},
		};
	}

	componentWillUnmount() {
		// this.state.marker.setMap(null);
	}

	vote(id, sentiment, value) {
		fetch("/api/vote", {
			method: 'POST',
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				id: id,
				[sentiment]: value,
			}),
		});
	}

	render() {
		return (
			<div className="tweet">
				<div
					className="x vote-only hidden"
					onClick={() => this.vote(this.state.id, "submit", true)}
				>
					x
				</div>
				<div className="text">
					{this.props.text}
				</div>
				{tm.sentiments.map(sentiment =>
					<Vote
						key={sentiment.key}
						sentiment={sentiment}
						vote={(sentiment, value) => this.vote(this.state.id, sentiment, value)}
					/>
				)}
			</div>
		);
	}
}
