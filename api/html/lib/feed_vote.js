class FeedVote extends HTMLElement {
	constructor() {
		super();

		$(document).children(`div`).on("click", ".vote>div", function() {
			var element = $(this);

			var data = {
				id: element.closest('.tweet').attr('id').split("_")[1]
			};

			for (sentiment of sentiments) {
				if (element.parent().hasClass(sentiment)) {
					data[sentiment] = element.hasClass('up');
				}
			}

			$.ajax({
				url: "/api/vote",
				method: "POST",
				data: data,
			}).done(function(data) {
				if (data != 'success') {
					return;
				}
				element.siblings().removeClass('voted');
				element.addClass('voted');
			});
		});

		$(document).on("mouseover", ".vote>div", function() {
			let $el = $(this);
			for (sentiment of sentiments) {
				if ($el.parent().hasClass(sentiment)) {
					$('#vote_description .' + sentiment).children($el.hasClass('up') ? '.up' : '.down').show();
				}
			}
		});

		$(document).on("mouseout", ".vote>div", function() {
			$('#vote_description').children().children().hide();
		});
	}
	connectedCallback() {
		$(this)
			.html(`
				<div class="up"></div>
				<div class="down"></div>
			`
			.children()
				.click(e => {
					var $element = $(e.target);

					var data = {
						id: $element.closest('.tweet').attr('id').split("_")[1]
					};

					sentiments.values.forEach(sentiment => {
						if (element.parent().hasClass(sentiment)) {
							data[sentiment] = element.hasClass('up');
						}
					});

					$.ajax({
						url: "/api/vote",
						method: "POST",
						data: data,
					}).done(function(data) {
						if (data != 'success') {
							return;
						}
						element.siblings().removeClass('voted');
						element.addClass('voted');
					});
				}
		;
	}
}

customElements.define('feed-vote', FeedVote);
