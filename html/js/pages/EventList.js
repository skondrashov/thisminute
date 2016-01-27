app.controller("EventListCtrl", ["$scope", "$location", "$timeout", "$http", "$interval",
    function($scope, $location, $timeout, $http, $interval) {
        
        $scope.data = [];
        
        $scope.now = new Date();
        
        $scope.search = { "$": "", "word": ""};
        
        $scope.renderLimit = 100;
        
        $scope.incrementRenderLimit = function(n) {
            $scope.renderLimit+= n;
        }
        
        $scope.resetRenderLimit = function(n) {
            $scope.renderLimit = n;
        }
        
        $scope.getTimeAgo = function(tweetTime) {
            var now = new Date();
            var yearsAgo = now.getUTCFullYear() - tweetTime.getUTCFullYear();
            if (yearsAgo >= 1) return Math.abs(yearsAgo) + " years ago";
            var monthsAgo = now.getUTCMonth() - tweetTime.getUTCMonth();
            if (monthsAgo >= 1) return Math.abs(monthsAgo) + " months ago";
            var daysAgo = now.getUTCDate() - tweetTime.getUTCDate();
            if (daysAgo >= 1) return Math.abs(daysAgo) + " days ago";
            var hoursAgo = now.getUTCHours() - tweetTime.getUTCHours();
            if (hoursAgo >= 1) return Math.abs(hoursAgo) + " hours ago";
            var minutesAgo = now.getUTCMinutes() - tweetTime.getUTCMinutes();
            if (minutesAgo >= 1) return Math.abs(minutesAgo) + " minutes ago";
        }
        
        
        // Initial functions
        update();
        $interval(update,10000);
        // End
        
        function update() {
            getNow();
            getEvents();
        }
        
        function getNow() {
            $scope.now = new Date();
        }
        
        function getEvents() {
            $http({
                url: app_server + "press/get_event_list.php",
                method: "GET",
            }).
            success(function(data) {
                fillEvents(data);
                console.log("Successfully retrieved data");
            }).
            error(function(data) {
                fillEvents(data);
                console.error("Error retrieving data");     
            });
        }
        
        function fillEvents(data) {
            $scope.data.length = 0;
            for (var key in data) {
                var datum = data[key];
                var tweet = new Tweet(datum.word, datum.time);
                $scope.data.push(tweet);
            }
        }
        
    }]);

