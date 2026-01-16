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

async function loadProducts(){
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/products?select=*&order=id.asc`,
    {
      headers:{
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${SUPABASE_KEY}`
      }
    }
  );

  const products = await res.json();
  servicesMap = {};

  products.forEach(p=>{
    const service = p.name.trim();

    if(!servicesMap[service]) servicesMap[service] = [];

    servicesMap[service].push({
      ...p,
      label: p.duration.trim()
    });
  });

  renderServices();
}

function renderServices(){
  grid.innerHTML = "";

  Object.keys(servicesMap).forEach(service=>{
    const first = servicesMap[service][0];

    const card = document.createElement("div");
    card.className = "service-card";
    card.innerHTML = `
      <div class="img-box">
        <img src="${first.image}" alt="${service}">
      </div>
      <span>${service}</span>
    `;
    card.onclick = ()=>openModal(service);
    grid.appendChild(card);
  });
}

function openModal(service){
  currentService = service;
  modalTitle.textContent = service;
  planSelect.innerHTML = "";

  const plans = servicesMap[service]; // نفس ترتيب Supabase

  plans.forEach((p,i)=>{
    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = p.label;
    planSelect.appendChild(opt);
  });

  updatePrice(service,0);
  modal.classList.remove("hidden");

  planSelect.onchange = e=>updatePrice(service,e.target.value);
}

function updatePrice(service,index){
  const p = servicesMap[service][index];
  currentPlan = p.label;
  priceValue.textContent = p.price;

  const msg =
`Hello, I would like to order:
${currentService}
Duration: ${currentPlan}
Price: ${p.price}`;

  buyBtn.href =
`https://wa.me/9613177862?text=${encodeURIComponent(msg)}`;
}

document.getElementById("closeModal").onclick =
()=>modal.classList.add("hidden");

document.getElementById("cancelBtn").onclick =
()=>modal.classList.add("hidden");

loadProducts();
