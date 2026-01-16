const SUPABASE_URL = "https://jcydjrcjwjtjedunziqk.supabase.co";
const SUPABASE_KEY = "sb_publishable_6ExmO6Dun-GiWE39_LKF2g_yYkAuQvo";

const grid = document.getElementById("servicesGrid");
const modal = document.getElementById("modal");
const modalTitle = document.getElementById("modalTitle");
const planSelect = document.getElementById("planSelect");
const priceValue = document.getElementById("priceValue");
const buyBtn = document.getElementById("buyBtn");

let servicesMap = {};
let currentService = "";
let currentPlan = "";

// ===== NORMALIZE SERVICE NAME =====
function normalizeName(name){
  return name.replace(/\s+/g," ").trim().toLowerCase();
}

// ===== PARSE DURATION TO SORT VALUE =====
// يحوّل:
// 1 Month -> 1
// 3 Months -> 3
// 1 Year -> 12
// 11 GB -> 11 (للباقات مثل Alfa Ushare)
function durationToValue(text){
  if(!text) return 0;
  const t = text.toLowerCase();
  const m = t.match(/(\d+)/);
  if(!m) return 0;
  const num = parseInt(m[1]);

  if(t.includes("year")) return num * 12;   // السنوات إلى أشهر
  if(t.includes("month")) return num;       // الأشهر
  if(t.includes("gb")) return num;          // الجيغابايت
  return num;                               // أي رقم آخر
}

// ===== LOAD PRODUCTS =====
async function loadProducts(){
  const res = await fetch(`${SUPABASE_URL}/rest/v1/products?select=*`,{
    headers:{
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`
    }
  });
  const products = await res.json();

  servicesMap = {};

  products.forEach(p=>{
    const key = normalizeName(p.name);

    if(!servicesMap[key]){
      servicesMap[key] = {
        title: p.name.trim(),
        items: []
      };
    }

    servicesMap[key].items.push(p);
  });

  renderServices();
}

// ===== RENDER SERVICES =====
function renderServices(){
  grid.innerHTML = "";

  Object.values(servicesMap).forEach(service=>{
    const first = service.items[0];

    const card = document.createElement("div");
    card.className = "service-card";
    card.innerHTML = `
      <div class="img-box">
        <img src="${first.image}" alt="${service.title}">
      </div>
      <span>${service.title}</span>
    `;
    card.onclick = ()=>openModal(service);
    grid.appendChild(card);
  });
}

// ===== SORT PLANS: SMALL -> BIG (GENERIC) =====
function sortPlans(plans){
  return plans.sort((a,b)=>{
    return durationToValue(a.duration) - durationToValue(b.duration);
  });
}

// ===== MODAL =====
function openModal(service){
  currentService = service.title;
  modalTitle.textContent = service.title;
  planSelect.innerHTML = "";

  let plans = sortPlans([...service.items]);

  plans.forEach((p,i)=>{
    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = p.duration;   // يظهر تمامًا كما كتبته في Supabase
    planSelect.appendChild(opt);
  });

  updatePrice(plans,0);
  modal.classList.remove("hidden");
  planSelect.onchange = e=>updatePrice(plans,e.target.value);
}

function updatePrice(plans,index){
  const p = plans[index];
  currentPlan = p.duration;
  priceValue.textContent = p.price;

  const msg = `Hello, I would like to order:%0A${currentService}%0ADuration: ${currentPlan}%0APrice: ${p.price}`;
  buyBtn.href = `https://wa.me/9613177862?text=${encodeURIComponent(msg)}`;
}

// ===== CLOSE MODAL =====
document.getElementById("closeModal").onclick = ()=>modal.classList.add("hidden");
document.getElementById("cancelBtn").onclick = ()=>modal.classList.add("hidden");

loadProducts();
