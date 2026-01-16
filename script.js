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

// ================= FETCH =================
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
    const service = p.name.trim();

    if(!servicesMap[service]) servicesMap[service] = [];

    servicesMap[service].push({
      ...p,
      label: p.duration.trim()
    });
  });

  renderServices();
}

// ================= RENDER CARDS =================
function renderServices(){
  grid.innerHTML = "";

  Object.keys(servicesMap).forEach(service=>{
    const card = document.createElement("div");
    card.className = "service-card";
    card.innerHTML = `
      <div class="img-box">
        <img src="${servicesMap[service][0].image}" alt="${service}">
      </div>
      <span>${service}</span>
    `;
    card.onclick = ()=>openModal(service);
    grid.appendChild(card);
  });
}

// ================= SORT =================
function sortPlans(plans){
  return plans.sort((a,b)=>{
    const getNumber = txt=>{
      const m = txt.match(/(\d+)/);
      return m ? parseInt(m[1]) : 0;
    };

    const aNum = getNumber(a.label);
    const bNum = getNumber(b.label);

    return aNum - bNum;
  });
}

// ================= MODAL =================
function openModal(service){
  currentService = service;
  modalTitle.textContent = service;
  planSelect.innerHTML = "";

  let plans = sortPlans([...servicesMap[service]]);

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

// ================= PRICE =================
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

// ================= CLOSE =================
document.getElementById("closeModal").onclick =
()=>modal.classList.add("hidden");

document.getElementById("cancelBtn").onclick =
()=>modal.classList.add("hidden");

// ================= START =================
loadProducts();
