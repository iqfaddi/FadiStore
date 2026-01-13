const SUPABASE_URL = "https://jcydjrcjwjtjedunziqk.supabase.co";
const SUPABASE_KEY = "sb_publishable_6ExmO6Dun-GiWE39_LKF2g_yYkAuQvo";

function getCategory(name){
  if(!name) return "Products";
  return name.split("–")[0].split("-")[0].trim();
}

async function loadProducts(){
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/products?select=*`,
    {
      headers:{
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${SUPABASE_KEY}`
      }
    }
  );

  const data = await res.json();

  if(!Array.isArray(data)){
    console.error("Supabase error:", data);
    return;
  }

  const wrap = document.getElementById("products");
  wrap.innerHTML = "";

  const grouped = {};

  // ترتيب حسب ID
  data
    .sort((a,b)=>a.id - b.id)
    .forEach(p=>{
      const cat = getCategory(p.name);
      if(!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(p);
    });

  Object.keys(grouped).forEach(cat=>{
    const sec = document.createElement("div");
    sec.className = "category";
    sec.innerHTML = `<h2>${cat}</h2>`;
    
    grouped[cat].forEach(p=>{
      const msg = `Hello, I would like to order:\n${p.name}\nDuration: ${p.duration}\nPrice: ${p.price}`;
      const link = `https://wa.me/9613177862?text=${encodeURIComponent(msg)}`;

      sec.innerHTML += `
        <div class="card">
          <img src="${p.image}" alt="${p.name}"/>
          <h3>${p.name}</h3>
          <p>${p.duration}</p>
          <div class="price">${p.price}</div>
          <a class="btn" href="${link}" target="_blank">Order Now</a>
        </div>
      `;
    });

    wrap.appendChild(sec);
  });
}

loadProducts();
