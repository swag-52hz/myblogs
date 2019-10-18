$(function () {
  // 新闻列表功能
  let $newsLi = $(".news-nav ul li");
  let iPage = 1;  //默认第1页
  let iTotalPage = 1; //默认总页数为1
  let sCurrentTagId = 0; //默认分类标签为0
  let bIsLoadData = true;   // 是否正在向后台加载数据

  // 加载新闻列表信息
  fn_load_content();

  $newsLi.click(function () {
    // 点击分类标签，则为点击的标签加上一个class属性为active
    // 并移除其它兄弟元素上的，值为active的class属性
    $(this).addClass('active').siblings('li').removeClass('active');
    // 获取绑定在当前选中分类上的data-id属性值
    let sClickTagId = $(this).children('a').attr('data-id');

    if (sClickTagId !== sCurrentTagId) {
            sCurrentTagId = sClickTagId;  // 记录当前分类id
            // 重置分页参数
            iPage = 1;
            iTotalPage = 1;
            fn_load_content()
        }
  });

  //页面滚动加载相关
  $(window).scroll(function () {
    // 浏览器窗口高度
    let showHeight = $(window).height();

    // 整个网页的高度
    let pageHeight = $(document).height();

    // 页面可以滚动的距离
    let canScrollHeight = pageHeight - showHeight;

    // 页面滚动了多少,这个是随着页面滚动实时变化的
    let nowScroll = $(document).scrollTop();

    if ((canScrollHeight - nowScroll) < 100) {
      // 判断页数，去更新新闻数据
      if (!bIsLoadData) {
        bIsLoadData = true;
        // 如果当前页数据如果小于总页数，那么才去加载数据
        if (iPage < iTotalPage) {
          iPage += 1;
          $(".btn-more").remove();  // 删除标签
          // 去加载数据
          fn_load_content()
        } else {
          message.showInfo('已全部加载，没有更多内容！');
          $(".btn-more").remove();  // 删除标签
          $(".news-list").append($('<a href="javascript:void(0);" class="btn-more">已全部加载，没有更多内容！</a>'))

        }
      }
    }
  });

  // 新闻轮播图功能
  fn_load_banner();
  /*=== bannerStart ===*/
  let $banner = $('.banner');
  let $picLi = $(".banner .pic li");
  let $prev = $('.banner .prev');
  let $next = $('.banner .next');
  let $tabLi = $('.banner .tab li');
  let index = 0;

  // 小原点
  $tabLi.click(function () {
    index = $(this).index();
    $(this).addClass('active').siblings('li').removeClass('active');
    $picLi.eq(index).fadeIn(1500).siblings('li').fadeOut(1500);
  });
  // 点击切换上一张
  $prev.click(function () {
    index--;
    if (index < 0) {
      index = $tabLi.length - 1
    }
    $tabLi.eq(index).addClass('active').siblings('li').removeClass('active');
    $picLi.eq(index).fadeIn(1500).siblings('li').fadeOut(1500);
  }).mousedown(function () {
    return false
  });

  $next.click(function () {
    auto();
  }).mousedown(function () {
    return false
  });
  //  图片向前滑动
  function auto() {
    index++;
    index %= $tabLi.length;
    $tabLi.eq(index).addClass('active').siblings('li').removeClass('active');
    $picLi.eq(index).fadeIn(3000).siblings('li').fadeOut(3000);
  }

  // 定时器
  let timer = setInterval(auto, 2000);
  $banner.hover(function () {
    clearInterval(timer)
  }, function () {
    auto();
  });

  /*=== bannerEnd ===*/


  // 定义向后端获取新闻列表数据的请求
  function fn_load_content() {
    // let sCurrentTagId = $('.active a').attr('data-id');

    // 创建请求参数
    let sDataParams = {
      "tag_id": sCurrentTagId,
      "page": iPage
    };

    // 创建ajax请求
    $.ajax({
      // 请求地址
      url: "/news/",  // url尾部需要添加/
      // 请求方式
      type: "GET",
      data: sDataParams,
      // 响应数据的格式（后端返回给前端的格式）
      dataType: "json",
    })
      .done(function (res) {
        if (res.errno === "0") {
          iTotalPage = res.data.total_pages;  // 后端传过来的总页数
          if (iPage === 1) {
            $(".news-list").html("")
          }

          res.data.news.forEach(function (one_news) {
            let content = `
              <li class="news-item">
                 <a href="/news/${one_news.id}/" class="news-thumbnail" target="_blank">
                    <img src="${one_news.image_url}" alt="${one_news.title}" title="${one_news.title}">
                 </a>
                 <div class="news-content">
                    <h4 class="news-title"><a href="/news/${one_news.id}/">${one_news.title}</a></h4>
                    <p class="news-details">${one_news.digest}</p>
                    <div class="news-other">
                      <span class="news-type">${one_news.tag_name}</span>
                      <span class="news-time">${one_news.update_time}</span>
                      <span class="news-author">${one_news.author}</span>
                    </div>
                 </div>
              </li>`;
            $(".news-list").append(content)
          });

          $(".news-list").append($('<a href="javascript:void(0);" class="btn-more">滚动加载更多</a>'));
          // 数据加载完毕，设置正在加载数据的变量为false，表示当前没有在加载数据
          bIsLoadData = false;

        } else {
          // 登录失败，打印错误信息
          message.showError(res.errmsg);
        }
      })
      .fail(function () {
        message.showError('服务器超时，请重试！');
      });
  }

  function fn_load_banner() {
    $.ajax({
      // 请求地址
      url: "/news/banners/",  // url尾部需要添加/
      // 请求方式
      type: "GET",
      async: false
    })
      .done(function (res) {
        if (res.errno === "0") {
          let content = ``;
          let tab_content = ``;
          res.data.banners.forEach(function (one_banner, index) {
            if (index === 0){
              content = `
                <li style="display:block;"><a href="/news/${one_banner.news_id}/">
                 <img src="${one_banner.image_url}" alt="${one_banner.news_title}"></a></li>
              `;
              tab_content = `<li class="active"></li>`;
            } else {
              content = `
              <li><a href="/news/${one_banner.news_id}/"><img src="${one_banner.image_url}" alt="${one_banner.news_title}"></a></li>
              `;
              tab_content = `<li></li>`;
            }

            $(".pic").append(content);
            $(".tab").append(tab_content)
          });

        } else {
          // 登录失败，打印错误信息
          message.showError(res.errmsg);
        }
      })
      .fail(function () {
        message.showError('服务器超时，请重试！');
      });
  }

});