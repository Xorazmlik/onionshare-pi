$(function () {
  $(document).ready(function () {
    $('.chat-container').removeClass('no-js');
    var socket = io.connect(
      'http://' + document.domain + ':' + location.port + '/chat',
      { transports: ['websocket'] }
    );
    var current_username = $('#username').val().trim();
    function updateClock() {
      var now = new Date();
      var h = String(now.getHours()).padStart(2, '0');
      var m = String(now.getMinutes()).padStart(2, '0');
      var s = String(now.getSeconds()).padStart(2, '0');
      $('#header-clock').text(h + ':' + m + ':' + s + ' UTC');
    }
    updateClock();
    setInterval(updateClock, 1000);
    function setConnState(state) {
      var dot = $('#conn-indicator');
      var label = $('#conn-label');
      dot.removeClass('connected disconnected');
      label.removeClass('connected disconnected');
      if (state === 'connected') {
        dot.addClass('connected');
        label.addClass('connected').text('XAVFSIZ');
      } else if (state === 'disconnected') {
        dot.addClass('disconnected');
        label.addClass('disconnected').text('OFLAYN');
      } else {
        label.text('ULANMOQDA');
      }
    }
    socket.on('connect', function () {
      setConnState('connected');
    });
    socket.on('status', function (data) {
      addMessageToPanel(data, current_username, 'status');
    });
    socket.on('chat_message', function (data) {
      addMessageToPanel(data, current_username, 'chat');
    });
    socket.on('disconnect', function () {
      setConnState('disconnected');
      addMessageToPanel(
        { msg: '// ULANISH UZILDI — chat serveri oflayn' },
        current_username,
        'status'
      );
    });
    socket.on('connect_error', function () {
      setConnState('disconnected');
    });
    $('#new-message').on('keypress', function (e) {
      var code = e.keyCode || e.which;
      if (code === 13) {
        emitMessage(socket);
      }
    });
    var MAX_MSG = 2000;
    $('#new-message').on('input', function () {
      var len = $(this).val().length;
      var counter = $('#char-counter');
      counter.removeClass('warn over');
      if (len > 0) {
        counter.text(len + '/' + MAX_MSG);
        if (len >= MAX_MSG) {
          counter.addClass('over');
        } else if (len > MAX_MSG * 0.85) {
          counter.addClass('warn');
        }
      } else {
        counter.text('');
      }
    });
    $('#username').on('keyup', function (event) {
      if ($('#username').val() !== '' && $('#username').val() !== current_username) {
        if (event.keyCode === 13 || event.which === 13) {
          this.blur();
          current_username = updateUsername(socket) || current_username;
        }
      }
    });
    $(window).on('beforeunload', function (e) {
      e.preventDefault();
      e.returnValue = '';
      return '';
    });
  });
});
var addMessageToPanel = function (data, current_username, messageType) {
  var scrollDiff = getScrollDiffBefore();
  if (messageType === 'status') {
    addStatusMessage(data.msg);
    if (data.connected_users) {
      addUserList(data.connected_users, current_username);
      var count = data.connected_users.length;
      $('#user-count').text('[' + count + ']');
    }
  } else if (messageType === 'chat') {
    addChatMessage(data.username, data.msg);
  }
  scrollBottomMaybe(scrollDiff);
};
var emitMessage = function (socket) {
  var text = $('#new-message').val();
  if (!text.trim()) return;
  $('#new-message').val('');
  $('#char-counter').text('');
  $('#chat').scrollTop($('#chat')[0].scrollHeight);
  socket.emit('text', { msg: text });
};
var updateUsername = function (socket) {
  var username = $('#username').val();
  if (
    !checkUsernameExists(username) &&
    !checkUsernameTooLong(username) &&
    !checkUsernameAscii(username)
  ) {
    $.ajax({
      method: 'POST',
      url: 'http://' + document.domain + ':' + location.port + '/update-session-username',
      contentType: 'application/json',
      dataType: 'json',
      data: JSON.stringify({ 'username': username })
    }).done(function (response) {
      if (response.success && response.username === username) {
        socket.emit('update_username', { username: username });
      } else {
        addStatusMessage('// XATO: Foydalanuvchi nomini yangilash muvaffaqiyatsiz.');
      }
    });
    return username;
  }
  return false;
};
var createUserListHTML = function (connected_users, current_user) {
  var html = '';
  connected_users.slice().sort().forEach(function (username) {
    if (username !== current_user) {
      html += '<li>' + sanitizeHTML(username) + '</li>';
    }
  });
  return html;
};
var checkUsernameAscii = function (username) {
  $('#username-error').text('');
  if (!/^[\u0000-\u007f]*$/.test(username)) {
    $('#username-error').text('Faqat ASCII belgilar qo\'llab-quvvatlanadi.');
    return true;
  }
  return false;
};
var checkUsernameExists = function (username) {
  $('#username-error').text('');
  var match = $('#user-list li').filter(function () {
    return $(this).text() === username;
  });
  if (match.length) {
    $('#username-error').text('Bu nom allaqachon ishlatilmoqda.');
    return true;
  }
  return false;
};
var checkUsernameTooLong = function (username) {
  $('#username-error').text('');
  if (username.length > 128) {
    $('#username-error').text('Nom 128 belgidan oshmasligi kerak.');
    return true;
  }
  return false;
};
var getScrollDiffBefore = function () {
  return (
    $('#chat').scrollTop() -
    ($('#chat')[0].scrollHeight - $('#chat')[0].offsetHeight)
  );
};
var scrollBottomMaybe = function (scrollDiff) {
  if (scrollDiff >= 0) {
    $('#chat').scrollTop($('#chat')[0].scrollHeight);
  }
};
var addStatusMessage = function (message) {
  $('#chat').append('<p class="status">' + sanitizeHTML(message) + '</p>');
};
var addChatMessage = function (username, message) {
  $('#chat').append(
    '<p>' +
    '<span class="username">' + sanitizeHTML(username) + '</span>' +
    '<span class="message">' + sanitizeHTML(message) + '</span>' +
    '</p>'
  );
};
var addUserList = function (connected_users, current_username) {
  $('#user-list').html(createUserListHTML(connected_users, current_username));
};
var sanitizeHTML = function (str) {
  var temp = document.createElement('span');
  temp.textContent = str;
  return temp.innerHTML;
};
