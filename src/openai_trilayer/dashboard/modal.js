export function showModal(html){
  const d=document, wrap=d.createElement('div'); wrap.className='modal-wrap'; 
  wrap.innerHTML=`<div class="modal"><button class="close" aria-label="Close">×</button>${html}</div>`;
  d.body.appendChild(wrap);
  wrap.querySelector('.close').onclick=()=>wrap.remove();
}
