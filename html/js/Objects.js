function Tweet(word, time) {
    this.word = word || "";
    this.time = new Date(time) || new Date();
    this.hover = false;
    
    this.getMap = function() {
        var ms = this.time.getTime() / 1000;
        window.location = "http://ochre.info/map.php?word=" + this.word + 
                        "&time=" + ms;
    }
}