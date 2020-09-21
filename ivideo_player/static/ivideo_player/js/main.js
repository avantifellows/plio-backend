//Bucket Configurations

var bucketName = "avanti-fellows";
var IdentityPoolId = "ap-south-1:55666887-6fb4-4ec4-b023-1d496059109e";
var bucketRegion = "ap-south-1";

console.log("HELLO!!")
var script_tag = document.getElementById('main_js')
var times = script_tag.getAttribute('data-times')
console.log(times[0])
AWS.config.update({
        region: bucketRegion,
        credentials: new AWS.CognitoIdentityCredentials({
        IdentityPoolId: IdentityPoolId
        })
    });

    var s3 = new AWS.S3({
        apiVersion: '2020-07-01',
        params: {Bucket: bucketName}
});

//user configured metadata about the questions
var save_dir = 'answers';
var time_values = [2, 4, 6];
var questions_list = ['q1', 'q2', 'q3'];
var set_of_options = [['o1', 'o2'], ['op1', 'op2', 'op3', 'op4'], ['opt1', 'opt2', 'opt3']];
var vid_id = 'bTqVqk7FSmY';
var object_id = 'Mtr6k7Ugzv';

var answers = [];
for(i=0; i<time_values.length; i++){
  answers.push("");
}

//utility functions

//create a radio button for a specific option
function radio_btn(id, name, value){
  var button = document.createElement("input");
  button.type = "radio";
  button.id = id;
  button.name = name;
  button.value = value;

  return button;
};

//create a label for the radio button created above
function label_for_radio_btn(forAttribute, valueHTML){
  var label = document.createElement("label");
  label.htmlFor = forAttribute;
  label.innerHTML = valueHTML;

  return label;
};

//forces fullscreen to any element
function toggleFullScreen(elem) {
    // ## The below if statement seems to work better ## if ((document.fullScreenElement && document.fullScreenElement !== null) || (document.msfullscreenElement && document.msfullscreenElement !== null) || (!document.mozFullScreen && !document.webkitIsFullScreen)) {
    if ((document.fullScreenElement !== undefined && document.fullScreenElement === null) || (document.msFullscreenElement !== undefined && document.msFullscreenElement === null) || (document.mozFullScreen !== undefined && !document.mozFullScreen) || (document.webkitIsFullScreen !== undefined && !document.webkitIsFullScreen)) {
        if (elem.requestFullScreen) {
            elem.requestFullScreen();
        } else if (elem.mozRequestFullScreen) {
            elem.mozRequestFullScreen();
        } else if (elem.webkitRequestFullScreen) {
            elem.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
        } else if (elem.msRequestFullscreen) {
            elem.msRequestFullscreen();
        }
    }

    // if (elem.cancelFullScreen) {
    //     elem.cancelFullScreen();
    // } else if (elem.mozCancelFullScreen) {
    //     elem.mozCancelFullScreen();
    // } else if (elem.webkitCancelFullScreen) {
    //     elem.webkitCancelFullScreen();
    // } else if (elem.msExitFullscreen) {
    //     elem.msExitFullscreen();
    // }
    // cancel_func();

    // console.log(elem.webkitRequestFullScreen)
    // console.log(elem.webkitCancelFullScreen)
}

//Runs the code when the content loads on the webpage
document.addEventListener('DOMContentLoaded', () => { 
  // setting up the "Plyr" video player
  
  // Change "{}" to your options:
  // https://github.com/sampotts/plyr/#options
  
  const player = new Plyr('#player', {
    keyboard:{
      focused:false,
      global:false
    },
    invertTime:false,
    // fullscreen: {enabled: false}
  });

  // player.fullscreen.enter()

  player.on('play', event => {
      if (questions.style.display == 'none'){
      } else{
        player.pause()
      }
  });

  player.on('enterfullscreen', event => {
      screen.orientation.lock('landscape');
      // player.fullscreen.exit()
  });

  player.on('exitfullscreen', event => {
      screen.orientation.lock('landscape');
      // player.fullscreen.exit()
      console.log('exiting')
  });

  document.getElementById('player').setAttribute("data-plyr-embed-id", vid_id);
  player.play()
  // Expose player so it can be used from the console
  window.player = player;
  
  // Bind event listener
  function on(selector, type, callback) {
    document.querySelector(selector).addEventListener(type, callback, false);
  }

  //On click events for the "Submit" and "Dismiss" button
  
  // On Submit
  on('.js-submit', 'click', () => { 
      radio_root = document.getElementById('form-options');
      radio_values = document.getElementById('form-options').elements;
      var radio_value;

      // iterating on options and saving the value if checked
      for(var i = 0; i < radio_values.length; i++){
          if(radio_values[i].checked){
              radio_value = radio_values[i].value;
              answers[time_index] = radio_value;
              radio_values[i].checked = false;
              break;
          }
      }

      // removing all the options
      while (radio_root.firstChild) {
        radio_root.removeChild(radio_root.lastChild);
      }

      //logging the recorded option
      console.log(answers);

      const student_answers = {
          'answers': answers,
          'questions': questions_list,
          'options': set_of_options
      }
      const json_answers = JSON.stringify(student_answers)
      console.log(json_answers) 

      var fileName = object_id + '_' + student_id + '.json'
      var filePath = save_dir + '/' + fileName;

      console.log("http://avanti-fellows.s3.ap-south-1.amazonaws.com/" + filePath)
      s3.putObject({
              Key: filePath,
              ACL: 'public-read',
              Body: json_answers,
              ContentType: 'application/json'
          }, function (err) {
              if(err) {
                  reject('error');
              }
          }
      ).on('httpUploadProgress', function (progress) {
              var uploaded = parseInt((progress.loaded * 100) / progress.total);
              $("progress").attr('value', uploaded);
          }
      );

      questions.style.display = 'none';
      player.play();
      pause = false;

      player.fullscreen.enter()

      ref_time = player.currentTime;
      time_diff_threshold = 0.8;

      function is_valid(){
        if (player.currentTime - ref_time <= time_diff_threshold){
           setTimeout(check_validity, 500);
        } else {
          exit();
        }
      }

      async function check_validity(){
        const valid = await is_valid();
      }

      function exit(){
        console.log(player.currentTime - ref_time);

        loop();
      }

      check_validity();
  });
  
  // On Dismiss
  on('.js-dismiss', 'click', () => { 
      radio_root = document.getElementById('form-options');

      // removing all the options
      while (radio_root.firstChild) {
        radio_root.removeChild(radio_root.lastChild);
      } 

      questions.style.display = 'none'
      player.play()
      pause = false;

      player.fullscreen.enter()

      ref_time = player.currentTime;
      time_diff_threshold = 0.8;

      // waiting for some time to pass
      const interval = setInterval(function(){
          if (player.currentTime - ref_time > time_diff_threshold){
            clearInterval(interval);
          }
      }, 500)

      loop();
  });

  // On email submit button
  on('.js-submit-email', 'click', () => {
      event.preventDefault();
      let identifier = document.forms["validate"]["courriel"].value;//.trim();
      let no_email = document.getElementById("novalid_email");
      let no_num = document.getElementById("novalid_number");
      var num_match = identifier.match(/\d/g);

      //check for mobile number
      if(num_match && num_match.length==identifier.length){
        if(num_match.length!=10){
          no_num.style.display = "block";
          no_email.style.display = "none";
          return false;
        }
      }
      //check for email
      else{
        let at = identifier.indexOf("@");
        let point = identifier.lastIndexOf(".");

        if(at < 1 || point < (at + 2) || (point + 2) >= identifier.length){
          console.log("two");
          no_email.style.display = "block";
          no_num.style.display = "none";
          return false;
        }               
      }

      student_id = identifier;
      console.log(student_id);
      document.getElementById('email_container').style.display = "none";
      document.getElementById('container').style.display = "block";

      // toggleFullScreen(document.getElementById('grid-box'));
      player.fullscreen.enter()
      
      // player.fullscreen.exit()
  });
  
  // selecting the overlay element
  var questions = document.getElementById('overlayElement')

  // this threshold makes sure that the same question is not displayed twice
  // if the user seeks left or right
  var time_diff_threshold = 0.1

  // whether the video is paused currently due to overlay
  var pause = false;
  var time_index;

  // setInterval(
  function loop(){
    // this loop sets the time_index to the question which is nearest to the
    // player.currentTime

    player_time = player.currentTime
    if (isNaN(player_time) || questions.style.display == 'block'){
      setTimeout(loop, 100)
      return
    }

    show_overlay = false;
    for (i=0; i<time_values.length; i++) {
      diff = time_values[i] - player_time
      if (diff > time_diff_threshold || diff <= 0) {
        continue;
      }
      show_overlay = true;
      time_index = i;
      break;
    }

    if (player_time > time_values[time_values.length - 1] + time_diff_threshold){
      time_index = time_values.length
    }
    
    // sanity check that time_index is always less than the number of
    // time inputs at which questions appear
    if (time_index < time_values.length && show_overlay && questions.style.display == 'none' && !pause) {
        // pause player
        player.pause()

        player.toggleControls();

        // set the video as pause
        pause = true;

        // disable submit button by default
        submit_button = document.getElementById('submit');
        submit_button.disabled = true;

        //build elements for the question
        //build the text for question
        document.getElementById("question-popup").innerHTML = questions_list[time_index];

        //build the radio buttons and labels
        var options_list = document.getElementById("form-options").elements;
        var radio_root = document.getElementById("form-options");

        for(i=0; i<set_of_options[time_index].length; i++){
          if (set_of_options[time_index][i] != "") {
            // creating a radio button element and a corresponding label
            var radio = radio_btn("option"+i+1, "option", set_of_options[time_index][i]);
            var radio_label = label_for_radio_btn("option"+i+1, set_of_options[time_index][i]);

            // enable submit button once a radio button is clicked
            radio.addEventListener('change', function() {
                submit_button.disabled = false
            });

            radio.style.display = "inline-block";
            radio_label.style.display = 'inline-block';

            radio_root.appendChild(radio);
            radio_root.appendChild(radio_label);

            var linebreak = document.createElement("br");
            radio_root.appendChild(linebreak);

          } else {
            options_list[i].style.display = "none";
          }
        }

        // display question
        questions.style.display = 'flex';

        player.fullscreen.exit()

        setTimeout(function(){ $('html,body').animate({
          scrollTop: $("#overlayElement").offset().top},
          'slow'); }, 1000)
        

    } else {
      // console.log('still here')
      setTimeout(loop, 100);
      // loop();
    }
  }

  // Execute a function when the user releases a key on the keyboard
  $("#email_text").keypress(function(event) {
    // Number 13 is the "Enter" key on the keyboard
    if (event.keyCode === 13) {
      // Cancel the default action, if needed
      event.preventDefault();
      // Trigger the button element with a click
      $('#btn').click()
    }
  });

  loop();
});
