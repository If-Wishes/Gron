const SUPABASE_URL = "YOUR_SUPABASE_URL";
const SUPABASE_ANON_KEY = "YOUR_ANON_KEY";

const supabase = window.supabase.createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY
);

// USERS
export async function getUsers() {
  return await supabase.from("users").select("*");
}

export async function createUser(user) {
  return await supabase.from("users").insert([user]);
}

export async function deleteUser(id) {
  return await supabase.from("users").delete().eq("id", id);
}

// NUMBERS
export async function addNumbers(userId, numbers, country) {
  const formatted = numbers.map(num => ({
    user_id: userId,
    number: num,
    last3: num.slice(-3),
    country
  }));

  return await supabase.from("user_numbers").insert(formatted);
}

export async function getUserNumbers(userId) {
  return await supabase
    .from("user_numbers")
    .select("*")
    .eq("user_id", userId);
}

// OTP MATCHING
export async function getOtpsForUser(userId) {
  const { data: numbers } = await getUserNumbers(userId);

  const last3List = numbers.map(n => n.last3);

  return await supabase
    .from("otp_logs")
    .select("*")
    .in("phone_last3", last3List)
    .order("created_at", { ascending: false });
}
