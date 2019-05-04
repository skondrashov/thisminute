/* globals tm, google */
import React, { Component } from 'react';

import Votes from './votes';

tm.markers = {};

export default class extends Component {
	constructor(props) {
		super(props);

		// this.state = {
		// 	marker: new google.maps.Marker({
		// 		position: {lat: parseFloat(props.lat), lng: parseFloat(props.lon)},
		// 		map: tm.map,
		// 		icon: tm.highlighted_icon,
		// 	})
		// };

		let marker = new google.maps.Marker({
				position: {lat: parseFloat(props.lat), lng: parseFloat(props.lng)},
				map: tm.map,
				icon: tm.highlighted_icon,
			});

		tm.markers[props.id] = marker;
	}

	componentWillUnmount() {
		// this.state.marker.setMap(null);
	}

	render() {
		return (
			<div className="tweet">
				<div className="x vote-only hidden">x</div>
				<div className="text">
					{this.props.text}
				</div>
				<Votes/>
			</div>
		);
	}
}
