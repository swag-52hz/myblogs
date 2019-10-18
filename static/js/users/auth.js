$(function () {
  let $username = $('#user_name');  // 选择id为user_name的网页元素，需要定义一个id为user_name
  let $img = $(".form-item .captcha-graph-img img");  // 获取图像标签
  let sImageCodeId = "";  // 定义图像验证码ID值
  let $mobile = $('#mobile');  // 选择id为mobile的网页元素，需要定义一个id为mobile
  let $smsCodeBtn = $('.form-item .sms-captcha');  // 获取短信验证码按钮元素，需要定义一个id为input_smscode
  let $imgCodeText = $('#input_captcha');  // 获取用户输入的图片验证码元素，需要定义一个id为input_captcha
  let $register = $('.form-contain');  // 获取注册表单元素


  // 1、图片验证码逻辑
  // 通过uuid生成验证码编号
  // 拼接验证码地址
  // 设置验证码图片标签的src
  generateImageCode();  // 生成图像验证码图片
  $img.click(generateImageCode);  // 点击图片验证码生成新的图片验证码图片


  // 2、用户名验证逻辑
  $username.blur(function () {
    fn_check_usrname();
  });


  // 3、手机号验证逻辑
  // 判断用户手机号是否注册
  $mobile.blur(function () {
    fn_check_mobile();
  });


  // 4、发送短信验证码逻辑
  $smsCodeBtn.click(function () {
    // 判断手机号是否输入
    if (fn_check_mobile() !== "success") {
      return
    }

    // 判断用户是否输入图片验证码
    let text = $imgCodeText.val();  // 获取用户输入的图片验证码文本
    if (!text) {
        message.showError('请填写验证码！');
        return
    }

    if (!sImageCodeId) {
      message.showError('图片UUID为空');
      return
    }

    // 正常
    let SdataParams = {
      "mobile": $mobile.val(),   // 获取用户输入的手机号
      "text": text,   // 获取用户输入的图片验证码文本
      "image_code_id": sImageCodeId  // 获取图片UUID
    };

    // for test
    // let SdataParams = {
    //   "mobile": "1806508",   // 获取用户输入的手机号
    //   "text": "ha3d",  // 获取用户输入的图片验证码文本
    //   "image_code_id": "680a5a66-d9e5-4c3c-b8ea"  // 获取图片UUID
    // };

    // 向后端发送请求
    $.ajax({
      // 请求地址
      url: "/sms_codes/",
      // 请求方式
      type: "POST",
      // 向后端发送csrf token
      // headers: {
      //           // 根据后端开启的CSRFProtect保护，cookie字段名固定为X-CSRFToken
      //           "X-CSRFToken": getCookie("csrf_token")
      // },
      // data: JSON.stringify(SdataParams),
      data: JSON.stringify(SdataParams),
      // 请求内容的数据类型（前端发给后端的格式）
      contentType: "application/json; charset=utf-8",
      // 响应数据的格式（后端返回给前端的格式）
      dataType: "json",
      async: false
    })
      .done(function (res) {
        if (res.errno === "0") {
          // 倒计时60秒，60秒后允许用户再次点击发送短信验证码的按钮
           message.showSuccess('短信验证码发送成功');
          let num = 60;
          // 设置一个计时器
          let t = setInterval(function () {
            if (num === 1) {
              // 如果计时器到最后, 清除计时器对象
              clearInterval(t);
              // 将点击获取验证码的按钮展示的文本恢复成原始文本
              $smsCodeBtn.html("获取验证码");
            } else {
              num -= 1;
              // 展示倒计时信息
              $smsCodeBtn.html(num + "秒");
            }
          }, 1000);
        } else {
          message.showError(res.errmsg);
        }
      })
      .fail(function(){
        message.showError('服务器超时，请重试！');
      });

  });


  // 5、注册逻辑
  $register.submit(function (e) {
    // 阻止默认提交操作
    e.preventDefault();

    // 获取用户输入的内容
    let sUsername = $username.val();  // 获取用户输入的用户名字符串
    let sPassword = $("input[name=password]").val();
    let sPasswordRepeat = $("input[name=password_repeat]").val();
    let sMobile = $mobile.val();  // 获取用户输入的手机号码字符串
    let sSmsCode = $("input[name=sms_captcha]").val();

    // 判断用户名是否已注册
    if (fn_check_usrname() !== "success") {
      return
    }

    // 判断手机号是否为空，是否已注册
    if (fn_check_mobile() !== "success") {
      return
    }

    // 判断用户输入的密码是否为空
    if ((!sPassword) || (!sPasswordRepeat)) {
      message.showError('密码或确认密码不能为空');
      return
    }

    // 判断用户输入的密码和确认密码长度是否为6-20位
    if ((sPassword.length < 6 || sPassword.length > 20) ||
      (sPasswordRepeat.length < 6 || sPasswordRepeat.length > 20)) {
      message.showError('密码和确认密码的长度需在6～20位以内');
      return
    }

    // 判断用户输入的密码和确认密码是否一致
    if (sPassword !== sPasswordRepeat) {
      message.showError('密码和确认密码不一致');
      return
    }


    // 判断用户输入的短信验证码是否为6位数字
    if (!(/^\d{6}$/).test(sSmsCode)) {
      message.showError('短信验证码格式不正确，必须为6位数字！');
      return
    }

    // 发起注册请求
    // 1、创建请求参数
    let SdataParams = {
      "username": sUsername,
      "password": sPassword,
      "password_repeat": sPasswordRepeat,
      "mobile": sMobile,
      "sms_code": sSmsCode
    };

    // 2、创建ajax请求
    $.ajax({
      // 请求地址
      url: "/users/register/",  // url尾部需要添加/
      // 请求方式
      type: "POST",
      data: JSON.stringify(SdataParams),
      // 请求内容的数据类型（前端发给后端的格式）
      contentType: "application/json; charset=utf-8",
      // 响应数据的格式（后端返回给前端的格式）
      dataType: "json",
    })
      .done(function (res) {
        if (res.errno === "0") {
          // 注册成功
          message.showSuccess('恭喜你，注册成功！');
          setTimeout(function () {
            // 注册成功之后重定向到主页
            window.location.href = document.referrer;
          }, 1000)
        } else {
          // 注册失败，打印错误信息
          message.showError(res.errmsg);
        }
      })
      .fail(function(){
        message.showError('服务器超时，请重试！');
      });

  });


  // 生成一个图片验证码的编号，并设置页面中图片验证码img标签的src属性
  function generateImageCode() {
    // 1、生成一个图片验证码随机编号
    sImageCodeId = generateUUID();
    // 2、拼接请求url /image_codes/<uuid:image_code_id>/
    let imageCodeUrl = "/image_codes/" + sImageCodeId + "/";
    // 3、修改验证码图片src地址
    $img.attr('src', imageCodeUrl)

  }

  // 生成图片UUID验证码
  function generateUUID() {
    let d = new Date().getTime();
    if (window.performance && typeof window.performance.now === "function") {
      d += performance.now(); //use high-precision timer if available
    }
    let uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      let r = (d + Math.random() * 16) % 16 | 0;
      d = Math.floor(d / 16);
      return (c == 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
    return uuid;
  }

  // 判断用户名是否已经注册
  function fn_check_usrname() {
    let sUsername = $username.val();  // 获取用户名字符串
    let sReturnValue = "";

    if (sUsername === "") {
      message.showError('用户名不能为空！');
      return
    }

    if (!(/^\w{5,20}$/).test(sUsername)) {
      message.showError('请输入5-20个字符的用户名');
      return
    }

    // 发送ajax请求，去后端查询用户名是否存在
    $.ajax({
      url: '/usernames/' + sUsername + '/',
      type: 'GET',
      dataType: 'json',
      async: false
    })
      .done(function (res) {
        if (res.data.count !== 0) {
          message.showError(res.data.username + '已注册，请重新输入！');
          sReturnValue = ""
        } else {
          message.showInfo(res.data.username + '能正常使用！');
          sReturnValue = "success"
        }
      })
      .fail(function () {
        message.showError('服务器超时，请重试！');
        sReturnValue = ""
      });
    return sReturnValue
  }

  // 判断手机号是否注册
  function fn_check_mobile() {
    let sMobile = $mobile.val();  // 获取用户输入的手机号码字符串
    let sReturnValue = "";
    if (sMobile === "") {
      message.showError('手机号不能为空！');
      return
    }
    if (!(/^1[345789]\d{9}$/).test(sMobile)) {
      message.showError('手机号码格式不正确，请重新输入！');
      return
    }

    $.ajax({
      url: '/mobiles/' + sMobile + '/',
      type: 'GET',
      dataType: 'json',
      async: false
    })
      .done(function (res) {
        if (res.data.count !== 0) {
          message.showError(res.data.mobile + '已注册，请重新输入！');
          sReturnValue = ""
        } else {
          message.showSuccess(res.data.mobile + '能正常使用！');
          sReturnValue = "success"
        }
      })
      .fail(function () {
        message.showError('服务器超时，请重试！');
        sReturnValue = ""
      });
    return sReturnValue

  }

  // get cookie using jQuery
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      let cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        let cookie = jQuery.trim(cookies[i]);
        // Does this cookie string begin with the name we want?
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
  }

  // Setting the token on the AJAX request
  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
      }
    }
  });

});