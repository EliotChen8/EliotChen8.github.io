/* Research 页视频（_includes/research-entry.html）：
   去掉系统控制条，只留一个播放/暂停按钮。视频静音循环，滚到可见时才加载并播放，
   滚出视口就暂停；读者手动暂停后不再自动恢复。系统开启「减少动态效果」时不自动播放。
   脚本没加载时视频保留 controls，读者仍能用系统控制条播放 */
(function () {
  "use strict";

  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function init(frame) {
    var video = frame.querySelector("video");
    var button = frame.querySelector(".pub__play");
    if (!video || !button) return;

    var userPaused = reduceMotion;
    var icon = button.querySelector("i");
    var label = button.querySelector("span");

    video.removeAttribute("controls");
    button.hidden = false;

    function render() {
      var paused = video.paused;
      icon.className = "fas " + (paused ? "fa-play" : "fa-pause");
      label.textContent = paused ? "Play" : "Pause";
      button.setAttribute("aria-label", (paused ? "Play" : "Pause") + " video");
    }

    function play() {
      if (video.preload === "none") video.preload = "auto";
      var p = video.play();
      if (p && typeof p.catch === "function") p.catch(function () {});
    }

    button.addEventListener("click", function () {
      if (video.paused) {
        userPaused = false;
        play();
      } else {
        userPaused = true;
        video.pause();
      }
    });
    video.addEventListener("play", render);
    video.addEventListener("pause", render);
    render();

    if (!("IntersectionObserver" in window)) {
      if (!userPaused) play();
      return;
    }

    new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            if (!userPaused) play();
          } else if (!video.paused) {
            video.pause();
          }
        });
      },
      { threshold: 0.25 }
    ).observe(frame);
  }

  function start() {
    var frames = document.querySelectorAll(".pub__frame--video");
    for (var i = 0; i < frames.length; i++) init(frames[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
