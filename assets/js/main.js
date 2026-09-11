(function(){
  var d=document;
  // mobile menu
  var mb=d.querySelector('.menu-btn'),nav=d.getElementById('nav');
  if(mb&&nav){mb.addEventListener('click',function(){var o=nav.classList.toggle('open');mb.setAttribute('aria-expanded',o)});
    d.addEventListener('keydown',function(e){if(e.key==='Escape'&&nav.classList.contains('open')){nav.classList.remove('open');mb.setAttribute('aria-expanded','false');mb.focus()}})}

  // gallery "show more"
  var more=d.getElementById('more');
  if(more){more.addEventListener('click',function(){
    var h=d.querySelectorAll('.grid a[hidden]');for(var i=0;i<h.length&&i<24;i++)h[i].hidden=false;
    if(h.length<=24)more.parentNode.remove();})}

  // lightbox
  var links=[].slice.call(d.querySelectorAll('[data-lb]'));
  if(links.length&&window.HTMLDialogElement){
    var dl=d.createElement('dialog');dl.className='lb';dl.setAttribute('aria-label','Photo viewer');
    dl.innerHTML='<figure><img alt=""></figure><button class="x" aria-label="Close">&times;</button><button class="prev" aria-label="Previous photo">&#8249;</button><button class="next" aria-label="Next photo">&#8250;</button><p class="count" aria-live="polite"></p>';
    d.body.appendChild(dl);
    var im=dl.querySelector('img'),ct=dl.querySelector('.count'),cur=0,sx=0;
    function vis(){return links.filter(function(a){return !a.hidden})}
    function show(i){var v=vis();cur=(i+v.length)%v.length;var a=v[cur];im.src=a.href;im.alt=(a.querySelector('img')||{}).alt||'';ct.textContent=(cur+1)+' / '+v.length}
    links.forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();show(vis().indexOf(a));dl.showModal()})});
    dl.querySelector('.x').onclick=function(){dl.close()};
    dl.querySelector('.prev').onclick=function(){show(cur-1)};
    dl.querySelector('.next').onclick=function(){show(cur+1)};
    dl.addEventListener('click',function(e){if(e.target===dl||e.target.tagName==='FIGURE')dl.close()});
    dl.addEventListener('keydown',function(e){if(e.key==='ArrowLeft')show(cur-1);if(e.key==='ArrowRight')show(cur+1)});
    dl.addEventListener('touchstart',function(e){sx=e.touches[0].clientX},{passive:true});
    dl.addEventListener('touchend',function(e){var dx=e.changedTouches[0].clientX-sx;if(Math.abs(dx)>50)show(cur+(dx<0?1:-1))},{passive:true});
    dl.addEventListener('close',function(){im.removeAttribute('src')});
  }

  // booking request -> email
  var f=d.getElementById('book');
  if(f){f.addEventListener('submit',function(e){
    if(f.getAttribute('action'))return; // a real form endpoint (e.g. Formspree) is configured
    e.preventDefault();var v=new FormData(f),b='';
    v.forEach(function(val,k){b+=k+': '+val+'\n'});
    location.href='mailto:'+f.dataset.to+'?subject='+encodeURIComponent('Trip request - '+(v.get('Name')||''))+'&body='+encodeURIComponent(b);
    var s=d.getElementById('sent');if(s)s.hidden=false;})}
})();
